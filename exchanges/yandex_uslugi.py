import logging
import time
from typing import Sequence

from aiohttp import ClientSession
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from models.order import Order
from exchanges.base import Exchange
from utils.helpers import sanitize_text
from config import YANDEX_COOKIES

logger = logging.getLogger(__name__)


class YandexUslugiExchange(Exchange):
    name = "Яндекс.Услуги"

    def _create_driver(self, headless: bool = True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.set_page_load_timeout(30)
        return driver

    async def fetch_orders(self, session: ClientSession) -> Sequence[Order]:
        logger.debug("Fetching orders from Yandex.Uslugi via Selenium")
        driver = None
        try:
            driver = self._create_driver(headless=True)

            # Главная + cookies
            driver.get("https://uslugi.yandex.ru")
            time.sleep(2)

            if YANDEX_COOKIES:
                for pair in YANDEX_COOKIES.split("; "):
                    if "=" in pair:
                        name, value = pair.split("=", 1)
                        try:
                            driver.add_cookie({"name": name.strip(), "value": value.strip()})
                        except Exception:
                            pass
                driver.refresh()
                time.sleep(2)

            url = "https://uslugi.yandex.ru/orders"
            driver.get(url)
            time.sleep(5)

            current_url = driver.current_url
            page_title = driver.title

            logger.info("Yandex.Uslugi URL: %s", current_url)
            logger.info("Yandex.Uslugi title: %s", page_title)

            # Детектим капчу
            if "captcha" in current_url.lower() or "captcha" in page_title.lower() or "робот" in page_title.lower():
                logger.warning(
                    "Яндекс.Услуги: показана капча! Cookies протухли. "
                    "Обновите YANDEX_COOKIES в .env — зайдите на uslugi.yandex.ru вручную "
                    "и скопируйте cookies из браузера."
                )
                return []

            orders = []
            seen_urls = set()

            # Ищем любые ссылки на заказы
            order_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/order/']")
            logger.info("Found %d order link elements", len(order_links))

            for link in order_links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link.text.strip()
                    if not title or len(title) < 10:
                        continue

                    description = ""
                    price = ""
                    try:
                        card = link
                        for _ in range(3):
                            card = card.find_element(By.XPATH, "..")
                        full_text = card.text
                        if len(full_text) > len(title):
                            description = full_text.replace(title, "", 1).strip()

                        for sel in ["[class*='price']", "[class*='cost']", "strong"]:
                            elems = card.find_elements(By.CSS_SELECTOR, sel)
                            for e in elems:
                                t = e.text.strip()
                                if t and any(ch.isdigit() for ch in t):
                                    price = t
                                    break
                            if price:
                                break
                    except Exception:
                        pass

                    orders.append(
                        Order(
                            title=sanitize_text(title),
                            description=sanitize_text(description),
                            price=sanitize_text(price),
                            deadline="",
                            client="",
                            source=self.name,
                            url=href,
                        )
                    )
                except Exception as e:
                    logger.debug("Error parsing card: %s", e)

                if len(orders) >= 10:
                    break

            logger.info("Parsed %d orders from Yandex.Uslugi via Selenium", len(orders))
            return orders

        except Exception as exc:
            logger.exception("Error fetching from Yandex.Uslugi: %s", exc)
        finally:
            if driver:
                driver.quit()

        return []
