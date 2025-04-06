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
    """Returns the path to the application's configuration file."""
    return Path(user_config_path(APP_NAME, appauthor=False)) / CONFIG_FILE_NAME

def create_default_config() -> configparser.ConfigParser:
    """Creates a ConfigParser instance with default values."""
    config = configparser.ConfigParser()
    config[CREDENTIALS_SECTION] = {API_KEY_CONFIG_KEY: ""}
    config[SETTINGS_SECTION] = {OUTPUT_STYLE_CONFIG_KEY: DEFAULT_OUTPUT_STYLE}
    return config

def get_config() -> configparser.ConfigParser:
    """Retrieves the application's configuration."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    if config_file.exists():
        try:
            config.read(config_file)
        except configparser.Error as e:
            raise ConfigurationError(f"Error parsing configuration file {config_file}: {e}") from e
    else:
        config = create_default_config()
        write_config(config) # Create the config file with defaults.

    return config

def get_gemini_api_key() -> str:
    """Retrieves the Gemini API key from the environment or configuration file."""
    # 1. Check environment variable
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    # 2. Check configuration file
    config = get_config()
    try:
        api_key = config.get(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY)
        if api_key:
            return api_key
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass  # Handle cases where the section or key doesn't exist

    # 3. If not found, raise an exception
    raise ApiKeyNotFound("Gemini API key not found. Please set the GEMINI_API_KEY environment variable or configure it via the TUI.")

def save_gemini_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the configuration file."""
    config = get_config()
    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)
    config.set(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY, api_key)
    write_config(config)

def get_output_style() -> VALID_OUTPUT_STYLES:
    """Retrieves the configured output style."""
    config = get_config()
    try:
        output_style = config.get(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, fallback=DEFAULT_OUTPUT_STYLE)
        if output_style in get_args(VALID_OUTPUT_STYLES):
            return output_style # type: ignore
        else:
            console.print(f"[yellow]Warning:[/yellow] Invalid output style '{output_style}' in config file.  Falling back to default ('{DEFAULT_OUTPUT_STYLE}').", style="yellow")
            return DEFAULT_OUTPUT_STYLE # type: ignore
    except (configparser.NoSectionError, configparser.NoOptionError):
        return DEFAULT_OUTPUT_STYLE # type: ignore

def set_config_value(section: str, key: str, value: str) -> None:
     """Sets a configuration value in the specified section."""
     config = get_config()
     if not config.has_section(section):
          config.add_section(section)
     config.set(section, key, value)
     write_config(config)

def write_config(config: configparser.ConfigParser) -> None:
    """Writes the configuration to the configuration file."""
    config_file = get_config_file_path()
    try:
        # Ensure the config directory exists
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