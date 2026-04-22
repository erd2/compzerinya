import logging
import sys
import io

from config import LOG_LEVEL

LOG_FORMAT = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    stream=sys.stdout,
    format=LOG_FORMAT,
)

logger = logging.getLogger("freelance_bot")
