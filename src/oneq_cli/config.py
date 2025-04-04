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
    """Loads the configuration from the config file. Creates a default one if it doesn't exist."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    if config_file.exists():
        try:
            config.read(config_file)
        except configparser.Error as e:
            raise ConfigurationError(f"Error parsing configuration file {config_file}: {e}") from e
    else:
        console.print("No config file found, creating default...", style="yellow")
        # Create default config structure
        config[CREDENTIALS_SECTION] = {}
        config[SETTINGS_SECTION] = {OUTPUT_STYLE_CONFIG_KEY: DEFAULT_OUTPUT_STYLE}  # Set default output style
        try:
            _write_config(config) # Create the file.
        except ConfigurationError:
            #Don't raise, as the program should still function with a missing config.
            console.print("Failed to create default config file.", style="red")


    return config

def get_api_key(config: configparser.ConfigParser) -> str:
    """Retrieves the Gemini API key from the environment or the config file."""
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        try:
            api_key = config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
        except KeyError:
            raise ApiKeyNotFound("Gemini API key not found in environment or config file.")
    return api_key

def get_output_style(config: configparser.ConfigParser) -> VALID_OUTPUT_STYLES:
    """Retrieves the output style from the config file."""
    try:
        output_style = config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
        if output_style not in get_args(VALID_OUTPUT_STYLES):
            console.print(f"[yellow]Warning:[/yellow] Invalid output style '{output_style}' in config file. Falling back to default ('{DEFAULT_OUTPUT_STYLE}').", style="yellow")
            return DEFAULT_OUTPUT_STYLE
        return output_style # type: ignore # Safe because of check above
    except KeyError:
        return DEFAULT_OUTPUT_STYLE


def set_config_value(section: str, key: str, value: str) -> None:
    """Sets a value in the configuration file."""
    config = load_config()
    if section not in config:
        config[section] = {}
    config[section][key] = value
    _write_config(config)

def _write_config(config: configparser.ConfigParser) -> None:
    """Writes the configuration to the config file."""
    config_file = get_config_file_path()
    try:
        # Ensure the config directory exists
        config_dir = config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"Configuration saved to {config_file}", style="green")
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