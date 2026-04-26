"""
KEEP v2 — Structured Logger

Logs decisions, not raw data.
Every log entry includes pipeline_version for traceability.
"""

import sys
from loguru import logger

# Remove default handler
logger.remove()

# Structured console logging — decisions only, compact format
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[agent]}</cyan> | {message}",
    level="INFO",
    filter=lambda record: "agent" in record["extra"],
)

# File logging for full trace replay
logger.add(
    "logs/keep_v2_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[agent]} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    filter=lambda record: "agent" in record["extra"],
)

def get_logger(agent_name: str):
    """Return a logger bound to a specific agent name for traceability."""
    return logger.bind(agent=agent_name)
