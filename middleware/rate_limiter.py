import asyncio
import functools
import random
import time
from typing import Callable


def rate_limited(min_interval: float):
    def decorator(func: Callable):
        last_called = {"time": 0.0}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = min_interval - (time.time() - last_called["time"])
            if delay > 0:
                jitter = random.uniform(0, 2)
                await asyncio.sleep(delay + jitter)
            result = await func(*args, **kwargs)
            last_called["time"] = time.time()
            return result

        return wrapper

    return decorator
