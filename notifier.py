import logging
from aiogram import Bot
from aiogram.enums import ParseMode
from config import TELEGRAM_CHAT_ID
from exceptions import NotificationError

logger = logging.getLogger(__name__)

_bot: Bot | None = None

MAX_MESSAGE_LENGTH = 4000


def get_notification_bot() -> Bot:
    global _bot
    if _bot is None:
        from config import TELEGRAM_BOT_TOKEN
        _bot = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot


async def close_notification_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


async def send_notification(
    order_title: str,
    order_description: str,
    order_url: str,
    relevance: int,
    cover_letter: str = "",
) -> None:
    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID не настроен")
        return

    bot = get_notification_bot()

    # Формируем описание — обрезаем если слишком длинное
    desc = order_description[:1500] if len(order_description) > 1500 else order_description

    message = (
        f"<b>🔍 Найден релевантный заказ</b>\n"
        f"<b>Тема:</b> {order_title}\n"
        f"<b>Релевантность:</b> {relevance}%\n"
        f"<b>Ссылка:</b> <a href=\"{order_url}\">Открыть заказ</a>\n\n"
        f"<b>Описание:</b>\n{desc}\n\n"
    )

    if cover_letter:
        message += f"<b>📝 Отклик:</b>\n{cover_letter}"

    # Telegram лимит 4096 символов
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH - 3] + "..."

    try:
        await bot.send_message(
            chat_id=int(TELEGRAM_CHAT_ID),
            text=message,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Failed to send notification")
        raise NotificationError("Telegram notification failed") from exc
