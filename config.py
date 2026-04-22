import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
MY_SKILLS = os.getenv("MY_SKILLS", "").strip()
RELEVANCE_THRESHOLD = int(os.getenv("RELEVANCE_THRESHOLD", "70"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
KWORK_COOKIES = os.getenv("KWORK_COOKIES", "")
KWORK_LOGIN = os.getenv("KWORK_LOGIN", "")
KWORK_PASSWORD = os.getenv("KWORK_PASSWORD", "")
KWORK_USE_SELENIUM = os.getenv("KWORK_USE_SELENIUM", "false").lower() in ("1", "true", "yes")
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "true").lower() in ("1", "true", "yes")
YANDEX_COOKIES = os.getenv("YANDEX_COOKIES", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_PATH = os.getenv("DATABASE_PATH", "orders.db")
OPENROUTER_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "30"))

EXCHANGES = [
    "exchanges.kwork.KworkExchange",
    # "exchanges.yandex_uslugi.YandexUslugiExchange",  # Отключено: cookies протухли, нужна новая авторизация
]
