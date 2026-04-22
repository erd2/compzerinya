import re
from urllib.parse import urlparse


def validate_price(value: str) -> bool:
    if not value:
        return False
    cleaned = value.replace(" ", "").replace("₽", "").replace("$", "")
    return bool(re.match(r"^\d+(\.\d+)?$", cleaned))


def validate_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False
