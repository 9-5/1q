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
DEFAULT_OUTPUT_STYLE: VALID_OUTPUT_STYLES = "auto" # type: ignore

console = Console()

def get_config_file_path() -> Path:
    """Returns the path to the configuration file."""
    return Path(user_config_path(CONFIG_DIR_NAME, appauthor=False)) / CONFIG_FILE_NAME


def load_config() -> configparser.ConfigParser:
    """Loads the configuration from the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except configparser.Error as e:
        raise ConfigurationError(f"Error parsing configuration file {config_file}: {e}") from e
    return config


def get_gemini_api_key(config: configparser.ConfigParser) -> str:
    """
    Retrieves the Gemini API key from the configuration or environment variable.
    Raises ApiKeyNotFound exception if the key is not found in either location.
    """
    try:
        api_key = config.get(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY)
        return api_key
    except (configparser.NoSectionError, configparser.NoOptionError):
        # API key not in config file, check environment variable
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if api_key:
            return api_key
        else:
            # API key not found in config or environment
            raise ApiKeyNotFound("Gemini API key not found in configuration file or environment variable.")


def set_config_value(section: str, key: str, value: str) -> None:
    """Sets a configuration value in the config file."""
    config_file = get_config_file_path()
    config = load_config()

    if not config.has_section(section):
        config.add_section(section)

    config.set(section, key, value)

    try:
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