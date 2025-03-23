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
    return user_config_path(CONFIG_DIR_NAME, appauthor=False, appname=APP_NAME) / CONFIG_FILE_NAME

def _get_config() -> configparser.ConfigParser:
    """Loads the configuration from the config file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except Exception as e:
        raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e
    return config

def get_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from the environment variables or the config file."""
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    config = _get_config()
    try:
        return config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
    except KeyError:
        return None

def save_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the configuration file."""
    config = configparser.ConfigParser()
    config[CREDENTIALS_SECTION] = {API_KEY_CONFIG_KEY: api_key}
    _write_config(config)

def get_output_style() -> str:
    """Gets the configured output style."""
    config = _get_config()
    try:
        output_style = config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
        if output_style not in get_args(VALID_OUTPUT_STYLES): # type: ignore
            console.print(f"[yellow]Warning:[/yellow] Invalid output style '{output_style}' in config file. Using default: {DEFAULT_OUTPUT_STYLE}", style="yellow")
            return DEFAULT_OUTPUT_STYLE
        return output_style
    except KeyError:
        return DEFAULT_OUTPUT_STYLE

def set_output_style(output_style: str) -> None:
    """Sets the output style in the configuration file."""
    if output_style not in get_args(VALID_OUTPUT_STYLES): # type: ignore
        raise ValueError(f"Invalid output style: {output_style}. Must be one of {get_args(VALID_OUTPUT_STYLES)}") # type: ignore

    config = configparser.ConfigParser()
    try:
        config.read(get_config_file_path()) # Preserve existing settings
    except Exception:
        pass # It's okay if the file doesn't exist yet

    if not config.has_section(SETTINGS_SECTION):
        config.add_section(SETTINGS_SECTION)
    config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY] = output_style
    _write_config(config)

def _write_config(config: configparser.ConfigParser) -> None:
    """Writes the configuration to the config file."""
    config_file = get_config_file_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
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