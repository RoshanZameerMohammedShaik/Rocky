"""Logging setup for Rocky.AI."""

import logging
from pathlib import Path
from datetime import datetime
from rocky.config import get_config


def setup_logging() -> logging.Logger:
    """Setup logging for Rocky.AI."""
    config = get_config()
    log_dir = config.paths.logs
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main logger
    logger = logging.getLogger("rocky")
    logger.setLevel(logging.DEBUG)
    
    # File handler - all logs
    log_file = log_dir / "rocky.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_file = log_dir / "errors.log"
    error_handler = logging.FileHandler(error_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = "rocky") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
