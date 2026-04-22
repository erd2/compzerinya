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
from utils.selenium_login import KworkSeleniumSession
from config import (
    KWORK_COOKIES,
    KWORK_LOGIN,
    KWORK_PASSWORD,
    KWORK_USE_SELENIUM,
    SELENIUM_HEADLESS,
)

logger = logging.getLogger(__name__)


class KworkExchange(Exchange):
    name = "Kwork"

    def _create_driver(self, headless: bool = True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        # Прямой путь к закэшированному драйверу — без WDM
        import os
        driver_path = r"C:\Users\nothingness\.wdm\drivers\chromedriver\win64\146.0.7680.165\chromedriver-win32\chromedriver.exe"
        if os.path.exists(driver_path):
            service = Service(driver_path)
        else:
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver

    def _set_cookies(self, driver):
        """Устанавливает cookies из строки."""
        driver.get("https://kwork.ru")
        time.sleep(1)
        if KWORK_COOKIES:
            for pair in KWORK_COOKIES.split("; "):
                if "=" in pair:
                    name, value = pair.split("=", 1)
                    try:
                        driver.add_cookie({"name": name.strip(), "value": value.strip()})
                    except Exception:
                        pass
            driver.refresh()
            time.sleep(2)

    def _login_if_needed(self, driver):
        """Авторизация через Selenium если cookies нет."""
        if not KWORK_COOKIES and KWORK_USE_SELENIUM and KWORK_LOGIN and KWORK_PASSWORD:
            logger.info("Logging in to Kwork via Selenium")
            selenium_session = KworkSeleniumSession(headless=SELENIUM_HEADLESS)
            try:
                cookies, logged_in = selenium_session.login(KWORK_LOGIN, KWORK_PASSWORD)
                if logged_in:
                    logger.info("Kwork Selenium login successful")
                else:
                    logger.warning("Kwork Selenium login failed")
            finally:
                selenium_session.close()

    def _get_full_description(self, driver, url, timeout=15):
        """Переходит на страницу заказа и забирает полное описание."""
        try:
            driver.get(url)
            time.sleep(3)

            # Ищем блок описания на странице проекта
            desc_selectors = [
                ".project-description",
                '[class*="project-desc"]',
                '[class*="want-desc"]',
                '[class*="description"]',
                'p',
            ]

            for sel in desc_selectors:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for elem in elems:
                    text = elem.text.strip()
                    if len(text) > 50:
                        # Убираем кнопки "Показать полностью"
                        text = text.replace("Показать полностью", "").strip()
                        return text

            # Фоллбэк: берём весь текст страницы и вырезаем лишнее
            body = driver.find_element(By.CSS_SELECTOR, "body")
            full_text = body.text
            # Оставляем только первые 1000 символов релевантного текста
            return full_text[:1000] if len(full_text) > 1000 else full_text

        except Exception as e:
            logger.debug("Error getting full description: %s", e)
            return ""

    async def fetch_orders(self, session: ClientSession) -> Sequence[Order]:
        logger.debug("Fetching orders from Kwork via Selenium")
        driver = None
        try:
            headless = SELENIUM_HEADLESS if KWORK_USE_SELENIUM else True
            driver = self._create_driver(headless=headless)

            # Авторизация
            if KWORK_COOKIES:
                self._set_cookies(driver)
            else:
                self._login_if_needed(driver)

            # Переходим на страницу заказов
            driver.get("https://kwork.ru/projects?c=11")

            # Ждём загрузки
            try:
                wait = WebDriverWait(driver, 20)
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[href^='/projects/']")
                    )
                )
                time.sleep(3)
            except Exception:
                logger.warning("Timeout waiting for Kwork project cards")

            # Шаг 1: собираем все URL и заголовки со страницы списка
            project_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='/projects/']")
            logger.info("Found %d project link elements", len(project_links))

            url_data = []  # (url, title, price)
            seen = set()
            for link in project_links:
                try:
                    href = link.get_attribute("href") or ""
                    if "/projects/list/" in href:
                        continue
                    if href.startswith("/"):
                        full_url = f"https://kwork.ru{href}"
                    else:
                        full_url = href
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    title = link.text.strip()
                    if not title or len(title) < 5:
                        continue

                    # Цена из карточки
                    price = ""
                    try:
                        card = link
                        for _ in range(4):
                            card = card.find_element(By.XPATH, "..")
                        for sel in ["[class*='price']", "[class*='cost']", "[class*='budget']", "strong"]:
                            for pe in card.find_elements(By.CSS_SELECTOR, sel):
                                pt = pe.text.strip()
                                if pt and any(c.isdigit() for c in pt):
                                    price = pt
                                    break
                            if price:
                                break
                    except Exception:
                        pass

                    url_data.append((full_url, title, price))
                    if len(url_data) >= 10:
                        break
                except Exception:
                    continue

            # Шаг 2: ходим за полными описаниями
            orders = []
            for full_url, title, price in url_data:
                try:
                    desc = self._get_full_description(driver, full_url)
                    orders.append(
                        Order(
                            title=sanitize_text(title),
                            description=sanitize_text(desc, max_length=2000),
                            price=sanitize_text(price),
                            deadline="",
                            client="",
                            source=self.name,
                            url=full_url,
                        )
                    )
                    logger.debug("  -> title='%s' desc_len=%d", title[:50], len(desc))
                except Exception as e:
                    logger.debug("Error getting description for %s: %s", full_url, e)
                    continue

            logger.info("Parsed %d orders from Kwork via Selenium", len(orders))
            return orders

        except Exception as exc:
            logger.exception("Error fetching from Kwork via Selenium: %s", exc)
        finally:
            if driver:
                driver.quit()

        # Fallback
        logger.info("Using fallback sample order for Kwork")
        return [
            Order(
                title="Разработка Python-скрипта для парсинга",
                description=sanitize_text(
                    "Нужно сделать парсер для сайтов фриланса с сохранением в SQLite."
                ),
                price="1500",
                deadline="3 дня",
                client="KworkClient",
                source=self.name,
                url="https://kwork.ru/projects/123",
            )
        ]
