import re
from urllib.parse import urlparse


def sanitize_text(value: str, max_length: int = 500) -> str:
    cleaned = re.sub(r"<[^>]+>", "", value)
    # Убираем "Показать полностью" и похожие
    cleaned = re.sub(r"\s*Показать полностью\s*", " ", cleaned)
    # Убираем "ПРОСМОТРЕНО"
    cleaned = re.sub(r"\s*ПРОСМОТРЕНО\s*", "", cleaned)
    # Убираем информацию о покупателе — не относится к заказу
    cleaned = re.sub(
        r"\s*[A-ZА-Я]?\s*Покупатель:\s*\S+\s*", " ", cleaned
    )
    cleaned = re.sub(
        r"\s*Размещено проектов на бирже:\s*\d+\s*", " ", cleaned
    )
    cleaned = re.sub(
        r"\s*Нанято:\s*\d+%\s*", " ", cleaned
    )
    cleaned = re.sub(
        r"\s*Осталось:\s*\S+\s*", " ", cleaned
    )
    cleaned = re.sub(
        r"\s*Предложений:\s*\d+\s*", " ", cleaned
    )
    # Убираем бюджеты — это не описание
    cleaned = re.sub(
        r"\s*Желаемый бюджет:\s*[^ \n]+", "", cleaned
    )
    cleaned = re.sub(
        r"\s*Допустимый:\s*[^ \n]+", "", cleaned
    )
    cleaned = re.sub(
        r"\s*Цена до:\s*[^ \n]+", "", cleaned
    )
    # Убираем одиночные буквы (инициалы)
    cleaned = re.sub(r"\s+[A-ZА-Я]\s+", " ", cleaned)
    cleaned = re.sub(r"^\s*[A-ZА-Я]\s+", "", cleaned)
    # Убираем "· Смотреть открытые (N)"
    cleaned = re.sub(r"\s*·\s*Смотреть открытые\s*\(\d+\)\s*", "", cleaned)
    # Чистим пробелы
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Обрезаем
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(" ", 1)[0] + "..."
    return cleaned


def is_valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False
