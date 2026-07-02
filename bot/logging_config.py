"""
Logging configuration for the trading bot.

Produces a single rotating log file (trading_bot.log) that captures:
- outgoing API requests (method, endpoint, params with secrets redacted)
- incoming API responses (status code, relevant body fields)
- errors and exceptions with context

Console output is kept separate and much lighter (INFO+ human-readable
summary only) so day-to-day usage isn't noisy, while the log file keeps
full detail for debugging / audit purposes.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root logger for the trading bot.

    - File handler: DEBUG level, detailed, rotates at 2MB (keeps 5 backups)
    - Console handler: INFO level, concise
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging() is called more than once
    if logger.handlers:
        return logger

    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def redact(params: dict) -> dict:
    """Return a copy of params with sensitive fields masked for logging."""
    redacted = dict(params)
    for key in ("signature", "apiKey", "api_key", "secret"):
        if key in redacted:
            redacted[key] = "***REDACTED***"
    return redacted
