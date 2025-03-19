import os
import configparser
from pathlib import Path

APP_NAME = "1q"
CONFIG_DIR_NAME = "1q"
CONFIG_FILE_NAME = "config.ini"
API_KEY_ENV_VAR = "GEMINI_API_KEY"

def get_config_file_path():
    config_dir = Path(os.path.expanduser(f"~/.config/{CONFIG_DIR_NAME}"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / CONFIG_FILE_NAME