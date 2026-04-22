import json
import logging
from aiohttp import ClientSession, ClientTimeout
from exceptions import LLMError
from utils.cache import TTLCache
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, MY_SKILLS, OPENROUTER_TIMEOUT

logger = logging.getLogger(__name__)
_llm_cache = TTLCache(ttl_seconds=300)
_cover_cache = TTLCache(ttl_seconds=3600)

PROMPT_TEMPLATE = (
    "Оцени соответствие заказа навыкам от 0 до 100. "
    "Навыки: {skills}. "
    "Верни только число."
)

COVER_PROMPT_TEMPLATE = (
    "Напиши короткий профессиональный отклик на фриланс-заказ. "
    "Навыки: {skills}. "
    "Напиши 2-3 предложения. Без лишних слов, без шаблонов. "
    "Покажи что ты понял задачу и готов выполнить. "
    "Не используй эмодзи. Начни сразу с предложения помощи."
)


async def evaluate_order(title: str, description: str) -> int:
    payload_key = _llm_cache.make_key(title, description)
    cached = await _llm_cache.get(payload_key)
    if cached is not None:
        logger.debug("LLM cache hit")
        return cached

    prompt = PROMPT_TEMPLATE.format(skills=MY_SKILLS)
    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты помогаешь оценивать релевантность заказов навыкам."},
            {"role": "user", "content": f"{prompt}\n\nНазвание: {title}\nОписание: {description}"},
        ],
        "temperature": 0,
        "max_tokens": 20,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    timeout = ClientTimeout(total=OPENROUTER_TIMEOUT)
    async with ClientSession(timeout=timeout) as session:
        try:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", json=body, headers=headers) as response:
                text = await response.text()
                if response.status != 200:
                    logger.error("LLM request failed: %s %s", response.status, text)
                    raise LLMError("OpenRouter API returned status %s" % response.status)
                data = await response.json()
        except Exception as exc:
            raise LLMError("LLM request failed") from exc

    if not isinstance(data, dict):
        raise LLMError("Unexpected response format from LLM")

    content = ""
    try:
        content = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise LLMError("Missing text response from LLM") from exc

    digits = "".join(ch for ch in content if ch.isdigit())
    if not digits:
        raise LLMError(f"Unable to parse relevance from LLM output: {content}")

    relevance = min(max(int(digits), 0), 100)
    await _llm_cache.set(payload_key, relevance)
    return relevance


async def generate_cover_letter(title: str, description: str) -> str:
    """Генерирует отклик на заказ."""
    cache_key = _cover_cache.make_key(title, description, MY_SKILLS)
    cached = await _cover_cache.get(cache_key)
    if cached is not None:
        return cached

    prompt = COVER_PROMPT_TEMPLATE.format(skills=MY_SKILLS)
    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты помогаешь составлять отклики на фриланс-заказы."},
            {"role": "user", "content": f"{prompt}\n\nНазвание: {title}\nОписание: {description}"},
        ],
        "temperature": 0.7,
        "max_tokens": 200,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    timeout = ClientTimeout(total=OPENROUTER_TIMEOUT)
    async with ClientSession(timeout=timeout) as session:
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions", json=body, headers=headers
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error("Cover letter API failed: %s %s", response.status, text)
                    return "Заинтересован в проекте. Готов обсудить детали."
                data = await response.json()
        except Exception as exc:
            logger.error("Cover letter request failed: %s", exc)
            return "Заинтересован в проекте. Готов обсудить детали."

    if not isinstance(data, dict):
        return "Заинтересован в проекте. Готов обсудить детали."

    try:
        content = data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Заинтересован в проекте. Готов обсудить детали."

    await _cover_cache.set(cache_key, content)
    return content
