import aiosqlite
from datetime import datetime
from typing import Optional

from config import DATABASE_PATH
from exceptions import DatabaseError
from models.order import Order

CREATE_ORDERS_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price TEXT,
    deadline TEXT,
    client TEXT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    relevance INTEGER,
    created_at TEXT NOT NULL
);
"""


async def init_db() -> None:
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(CREATE_ORDERS_SQL)
            await db.commit()
    except Exception as exc:
        raise DatabaseError("Unable to initialize database") from exc


async def order_exists(url: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT 1 FROM orders WHERE url = ?", (url,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def save_order(order: Order) -> Order:
    order.created_at = order.created_at or datetime.utcnow()
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO orders (title, description, price, deadline, client, source, url, relevance, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    order.title,
                    order.description,
                    order.price,
                    order.deadline,
                    order.client,
                    order.source,
                    order.url,
                    order.relevance,
                    order.created_at.isoformat(),
                ),
            )
            await db.commit()
            return order
    except Exception as exc:
        raise DatabaseError("Unable to save order") from exc


async def get_last_orders(limit: int = 10) -> list[Order]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT title, description, price, deadline, client, source, url, relevance, created_at "
            "FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            orders = []
            for row in rows:
                created_at = row[8]
                if created_at:
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        created_at = datetime.utcnow()
                else:
                    created_at = datetime.utcnow()

                orders.append(
                    Order(
                        title=row[0],
                        description=row[1],
                        price=row[2],
                        deadline=row[3],
                        client=row[4],
                        source=row[5],
                        url=row[6],
                        relevance=row[7],
                        created_at=created_at,
                    )
                )
            return orders
