from abc import ABC, abstractmethod
from aiohttp import ClientSession
from typing import Sequence

from models.order import Order


class Exchange(ABC):
    name: str

    @abstractmethod
    async def fetch_orders(self, session: ClientSession) -> Sequence[Order]:
        raise NotImplementedError
