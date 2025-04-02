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
            # Check if the API key exists, and raise an exception if it doesn't.
            if (CREDENTIALS_SECTION not in config or
                API_KEY_CONFIG_KEY not in config[CREDENTIALS_SECTION] or
                not config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]):
                raise ApiKeyNotFound("Gemini API key not found in configuration.")
        except Exception as e:
            raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e
    else:
        # If the file doesn't exist, treat it as if the API key is missing.
        raise ApiKeyNotFound("Configuration file not found. Gemini API key is missing.")

    return config

def save_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the config file."""
    config = configparser.ConfigParser()
    config[CREDENTIALS_SECTION] = {API_KEY_CONFIG_KEY: api_key}

    config_file = get_config_file_path()
    _write_config(config, config_file)

def get_output_style() -> VALID_OUTPUT_STYLES:
    """Gets the configured output style or returns the default."""
    config = load_config()
    try:
        style = config.get(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, fallback=DEFAULT_OUTPUT_STYLE)
        if style not in get_args(VALID_OUTPUT_STYLES):
            console.print(f"[yellow]Invalid output style '{style}' in config. Using default.[/yellow]")
            return DEFAULT_OUTPUT_STYLE
        return style
    except Exception:
        return DEFAULT_OUTPUT_STYLE

def set_output_style(style: str) -> None:
    """Sets the default output style in the config file."""
    if style not in get_args(VALID_OUTPUT_STYLES):
        raise ValueError(f"Invalid output style: {style}. Must be one of {get_args(VALID_OUTPUT_STYLES)}")

    config = configparser.ConfigParser()
    config[SETTINGS_SECTION] = {OUTPUT_STYLE_CONFIG_KEY: style}

    config_file = get_config_file_path()
    _write_config(config, config_file)

def _write_config(config: configparser.ConfigParser, config_file: Path) -> None:
    """Writes the configparser object to the config file, creating the directory if needed."""
    try:
        config_dir = config_file.parent
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