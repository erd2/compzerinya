from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    title: str
    description: str
    price: str
    deadline: str
    client: str
    source: str
    url: str
    created_at: datetime | None = None
    relevance: int | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "deadline": self.deadline,
            "client": self.client,
            "source": self.source,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "relevance": self.relevance,
        }
