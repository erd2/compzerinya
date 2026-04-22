import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import TELEGRAM_BOT_TOKEN, MY_SKILLS, RELEVANCE_THRESHOLD, POLL_INTERVAL_SECONDS
from db import get_last_orders
from llm import evaluate_order, generate_cover_letter
from logging_config import logger
from notifier import close_notification_bot
from scheduler import worker


def validate_config() -> list[str]:
    """Проверяет обязательные настройки. Возвращает список ошибок."""
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не задан в .env")
    if not MY_SKILLS:
        errors.append("MY_SKILLS не задан — бот не сможет оценивать заказы")
    if RELEVANCE_THRESHOLD < 0 or RELEVANCE_THRESHOLD > 100:
        errors.append("RELEVANCE_THRESHOLD должен быть от 0 до 100")
    if POLL_INTERVAL_SECONDS < 10:
        errors.append("POLL_INTERVAL_SECONDS слишком маленький (минимум 10)")
    return errors


def create_bot() -> Bot:
    return Bot(token=TELEGRAM_BOT_TOKEN)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Бот запущен. Я буду проверять заказы и отправлять уведомления.\n\n"
            "Команды:\n"
            "/stats — последние заказы\n"
            "/cover <ссылка> — сгенерировать отклик\n"
            "/stop — остановить бота"
        )

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        orders = await get_last_orders(limit=5)
        if not orders:
            await message.answer("Пока нет сохранённых заказов.")
            return
        text = "Последние заказы:\n\n"
        for order in orders:
            rel = order.relevance if order.relevance is not None else "?"
            text += f"{order.source}: {order.title} — {rel}%\n"
        await message.answer(text)

    @dp.message(Command("stop"))
    async def cmd_stop(message: Message) -> None:
        await message.answer("Бот останавливается.")
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()

    @dp.message(Command("cover"))
    async def cmd_cover(message: Message) -> None:
        args = message.text.split(maxsplit=1)
        if len(args) < 2 or not args[1].startswith("http"):
            await message.answer(
                "Использование: /cover <ссылка_на_заказ>\n"
                "Пример: /cover https://kwork.ru/projects/3148645"
            )
            return

        url = args[1].strip()
        status_msg = await message.answer("⏳ Загружаю заказ и генерирую отклик...")

        try:
            # Извлекаем title и description из страницы
            from aiohttp import ClientSession
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager
            from utils.helpers import sanitize_text

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=opts
            )
            try:
                driver.get(url)
                import time
                time.sleep(3)

                title = driver.title or ""
                body = driver.find_element(By.CSS_SELECTOR, "body")
                desc = body.text[:1500] if body.text else ""

                desc = sanitize_text(desc, max_length=1500)
                title = sanitize_text(title, max_length=200)

                cover = await generate_cover_letter(title, desc)

                response = f"<b>📝 Отклик для:</b>\n{title}\n\n{cover}"
                await message.answer(response, parse_mode="HTML")
            finally:
                driver.quit()

            await status_msg.delete()
        except Exception as exc:
            logger.exception("Cover generation failed")
            await message.answer(f"❌ Ошибка: {exc}")

    return dp


async def main() -> None:
    # Валидация конфигурации
    config_errors = validate_config()
    if config_errors:
        logger.error("Ошибки конфигурации:")
        for err in config_errors:
            logger.error("  - %s", err)
        return

    bot = create_bot()
    dp = create_dispatcher()

    scheduler_task = asyncio.create_task(worker())

    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info("Запуск polling (попытка %d/%d)", attempt + 1, max_retries)
            await dp.start_polling(bot)
            break
        except Exception as exc:
            if "timeout" in str(exc).lower() or "network" in str(exc).lower():
                logger.warning("Сеть: %s. Повтор через 10 сек...", exc)
                await asyncio.sleep(10)
            else:
                raise
    else:
        logger.error("Не удалось запустить бота после %d попыток", max_retries)

    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    await close_notification_bot()
    await bot.session.close()
    logger.info("Бот остановлен")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
