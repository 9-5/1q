import os
import configparser
from pathlib import Path
import sys
from typing import Optional, Tuple, Literal
try:
    from typing import get_args
except ImportError:
    # Basic fallback for Python < 3.8
    def get_args(tp):
        return getattr(tp, '__args__', ())

from platformdirs import user_config_path
from rich.console import Console

from .exceptions import ApiKeyNotFound, ConfigurationError

APP_NAME = "1q"
CONFIG_DIR_NAME = "1q"
CONFIG_FILE_NAME = "config.ini"
API_KEY_ENV_VAR = "GEMINI_API_KEY"

CREDENTIALS_SECTION = "Credentials"
API_KEY_CONFIG_KEY = "gemini_api_key"
SETTINGS_SECTION = "Settings"
OUTPUT_STYLE_CONFIG_KEY = "output_style"

VALID_OUTPUT_STYLES = Literal["auto", "tui", "inline"]
DEFAULT_OUTPUT_STYLE: VALID_OUTPUT_STYLES = "auto"

console = Console()

def get_config_dir_path() -> Path:
    """Returns the path to the application's configuration directory."""
    return Path(user_config_path(APP_NAME, appauthor=False))

def get_config_file_path() -> Path:
    """Returns the path to the configuration file."""
    return get_config_dir_path() / CONFIG_FILE_NAME

def load_config() -> configparser.ConfigParser:
    """Loads the configuration from the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    if config_file.exists():
        try:
            config.read(config_file)
        except configparser.Error as e:
            raise ConfigurationError(f"Error parsing configuration file {config_file}: {e}") from e
    return config

def save_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the config file."""
    config = load_config()
    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)
    config.set(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY, api_key)
    _write_config(config)

def set_default_output_style(output_style: str) -> None:
     """Sets the default output style in the config file."""
     if output_style not in get_args(VALID_OUTPUT_STYLES):
          raise ValueError(f"Invalid output style: {output_style}.  Must be one of {get_args(VALID_OUTPUT_STYLES)}")

     config = load_config()
     if not config.has_section(SETTINGS_SECTION):
          config.add_section(SETTINGS_SECTION)
     config.set(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, output_style)
     _write_config(config)

def _write_config(config: configparser.ConfigParser) -> None:
    """Writes the configuration to the config file."""
    config_file = get_config_file_path()
    try:
        # Ensure the config directory exists
        config_dir = get_config_dir_path()
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e


def clear_config_file() -> None:
    """Removes the entire configuration file."""
    config_file = get_config_file_path()
    if config_file.exists():
        try:
            os.remove(config_file)
            console.print(f"Configuration file removed: {config_file}", style="green")
        except OSError as e:
            console.print(f"[red]Error:[/red] Could not remove configuration file {config_file}: {e}", style="red")
    else:
        console.print("Configuration file does not exist. Nothing to clear.", style="yellow")