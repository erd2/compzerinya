import asyncio
import importlib
import logging
from aiohttp import ClientSession

from config import EXCHANGES, POLL_INTERVAL_SECONDS, RELEVANCE_THRESHOLD
from db import init_db, order_exists, save_order
from llm import evaluate_order, generate_cover_letter
from notifier import send_notification
from models.order import Order
from logging_config import logger
from middleware.rate_limiter import rate_limited


async def load_exchange(path: str):
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()


async def process_order(order: Order) -> None:
    try:
        if await order_exists(order.url):
            logger.debug("Order already exists: %s", order.url)
            return

        order.relevance = await evaluate_order(order.title, order.description)
        await save_order(order)

        if order.relevance is not None and order.relevance >= RELEVANCE_THRESHOLD:
            cover = await generate_cover_letter(order.title, order.description)
            await send_notification(
                order.title, order.description, order.url, order.relevance, cover_letter=cover
            )
        else:
            logger.info("Order skipped by relevance %s: %s", order.relevance, order.url)
    except Exception as exc:
        logger.exception("Error processing order %s", order.url)


async def worker() -> None:
    await init_db()
    exchange_instances = [await load_exchange(path) for path in EXCHANGES]
    logger.info("Loaded exchanges: %s", [e.name for e in exchange_instances])

    async with ClientSession() as session:
        while True:
            tasks = []
            for exchange in exchange_instances:
                tasks.append(fetch_and_process(exchange, session))
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


@rate_limited(10)
async def fetch_and_process(exchange, session: ClientSession) -> None:
    logger.info("Fetching orders from %s", exchange.name)
    try:
        orders = await exchange.fetch_orders(session)
        for order in orders:
            await process_order(order)
    except Exception as exc:
        logger.exception("Exchange fetch failed: %s", exchange.name)
