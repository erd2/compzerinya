import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class KworkSeleniumSession:
    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def create_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        return self.driver

    def login(self, username: str, password: str) -> tuple[str, bool]:
        if not self.driver:
            self.create_driver()

        self.driver.get("https://kwork.ru/login")
        wait = WebDriverWait(self.driver, self.timeout)

        login_input = None
        password_input = None
        submit_button = None

        try:
            login_input = wait.until(
                EC.presence_of_element_located((By.NAME, "login"))
            )
        except Exception:
            login_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")

        try:
            password_input = self.driver.find_element(By.NAME, "password")
        except Exception:
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        login_input.clear()
        login_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)

        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except Exception:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button")

        submit_button.click()

        login_success = False
        try:
            wait.until(EC.url_contains("/projects"))
            login_success = True
        except Exception:
            time.sleep(3)
            login_success = "/projects" in self.driver.current_url

        cookies = self.driver.get_cookies()
        cookie_string = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)

        if login_success and cookie_string:
            logger.info("Selenium login succeeded for Kwork")
        else:
            logger.warning("Selenium login failed or cookies not found for Kwork")

        return cookie_string, login_success

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
