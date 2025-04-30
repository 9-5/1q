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

def get_config_file_path() -> Path:
    """Returns the path to the configuration file."""
    return Path(user_config_path(APP_NAME, appauthor=False)) / CONFIG_FILE_NAME


def load_config() -> configparser.ConfigParser:
    """Loads the configuration from the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except Exception as e:
        raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e
    return config


def get_api_key(config: Optional[configparser.ConfigParser]) -> str:
    """Retrieves the Gemini API key from the environment or config file."""
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        if config and config.has_option(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY):
            api_key = config.get(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY)
        else:
            raise ApiKeyNotFound(
                f"Gemini API key not found. Set the {API_KEY_ENV_VAR} environment variable or configure it using the TUI."
            )
    return api_key


def save_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()
    if config_file.exists():
        config.read(config_file)

    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)
    config.set(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY, api_key)

    try:
        # Ensure the config directory exists
        config_dir = config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"API key saved to configuration file: {config_file}", style="green")

    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e

def set_output_style(style: str) -> None:
    """Sets the default output style in the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()
    if config_file.exists():
        config.read(config_file)

    if not config.has_section(SETTINGS_SECTION):
        config.add_section(SETTINGS_SECTION)
    config.set(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, style)

    try:
        # Ensure the config directory exists
        config_dir = config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"Output style saved to configuration file: {config_file}", style="green")

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