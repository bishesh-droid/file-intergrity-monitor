# fim/logger.py

import logging
import os
from .config import LOG_FILE, LOG_DIR, LOG_LEVEL, VERBOSE_CONSOLE_OUTPUT

def setup_logging(log_level=LOG_LEVEL, console_output=VERBOSE_CONSOLE_OUTPUT):
    """
    Configures logging for the File Integrity Monitor.
    Logs to a file and optionally to the console.
    """
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Create a logger
    fim_logger = logging.getLogger('file_integrity_monitor')
    fim_logger.setLevel(log_level)
    fim_logger.propagate = False # Prevent messages from being passed to the root logger

    # Clear existing handlers to avoid duplicate logs
    if fim_logger.hasHandlers():
        fim_logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    fim_logger.addHandler(file_handler)

    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        fim_logger.addHandler(console_handler)

    return fim_logger

# Initialize logger when module is imported
fim_logger = setup_logging()