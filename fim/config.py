# fim/config.py

import os
import yaml
import logging

# Base directory for the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default paths
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, 'data')
DEFAULT_DATABASE_PATH = os.path.join(DEFAULT_DATA_DIR, 'fim_baseline.db')
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, 'logs')
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, 'fim.log')
DEFAULT_FIM_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'fim_config.yaml')

# Environment variable overrides
DATABASE_PATH = os.environ.get('FIM_DATABASE_PATH', DEFAULT_DATABASE_PATH)
LOG_FILE = os.environ.get('FIM_LOG_FILE', DEFAULT_LOG_FILE)
FIM_CONFIG_PATH = os.environ.get('FIM_CONFIG_PATH', DEFAULT_FIM_CONFIG_PATH)

# Load configuration from YAML file
def load_config(config_path=FIM_CONFIG_PATH):
    """
    Loads configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError) as e:
        logging.getLogger(__name__).error(f"Error loading config file {config_path}: {e}")
        return {}

# Global config object
config = load_config()

# Configuration settings with defaults
HASH_ALGORITHM = config.get('hash_algorithm', 'sha256')
LOG_LEVEL = config.get('log_level', 'INFO').upper()
VERBOSE_CONSOLE_OUTPUT = config.get('verbose_console_output', True)

# Ensure data and log directories exist
DATA_DIR = os.path.dirname(DATABASE_PATH)
LOG_DIR = os.path.dirname(LOG_FILE)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Map log level string to logging constants
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}
LOG_LEVEL = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)