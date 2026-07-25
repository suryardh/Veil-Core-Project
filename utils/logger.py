"""
utils/logger.py

Structured logger for Veil.
Outputs to both console (colored) and a rotating log file.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler

import config

LOG_FORMAT = "%(message)s"
DATE_FORMAT = "[%X]"

def get_logger(name: str = "veil") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_file = os.path.join(config.LOG_DIR, "veil.log")

    console_handler = RichHandler(rich_tracebacks=True, show_path=False, log_time_format=DATE_FORMAT)
    console_handler.setLevel(logging.INFO)

    os.makedirs(config.LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(fmt="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

log = get_logger("veil")
