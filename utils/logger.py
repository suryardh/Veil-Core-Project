"""
utils/logger.py

Structured logger for Veil.
Outputs to both console (colored) and a rotating log file.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import config

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_COLORS = {
    "DEBUG":    "\033[36m",
    "INFO":     "\033[32m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[35m",
    "RESET":    "\033[0m",
}


class _ColorFormatter(logging.Formatter):
    def format(self, record):
        original = record.levelname
        color = _COLORS.get(original, _COLORS["RESET"])
        record.levelname = f"{color}{original}{_COLORS['RESET']}"
        formatted = super().format(record)
        record.levelname = original
        return formatted


def get_logger(name: str = "veil") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_file = os.path.join(config.LOG_DIR, "veil.log")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        _ColorFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    )

    os.makedirs(config.LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


log = get_logger("veil")
