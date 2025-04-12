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

def get_gemini_api_key() -> str:
    """
    Retrieves the Gemini API key from the environment variables or the configuration file.
    Raises ApiKeyNotFound if the key is not found in either location.
    """
    # 1. Check environment variable
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    # 2. Check configuration file
    config_file = get_config_file_path()
    if config_file.exists():
        config = configparser.ConfigParser()
        try:
            config.read(config_file)
            if CREDENTIALS_SECTION in config and API_KEY_CONFIG_KEY in config[CREDENTIALS_SECTION]:
                return config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
        except Exception as e:
            raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e

    # 3. If not found in either location, raise an exception
    raise ApiKeyNotFound("Gemini API key not found in environment variables or configuration file.")

def save_gemini_api_key(api_key: str) -> None:
    """Saves the Gemini API key to the configuration file."""
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    # Read existing config if it exists, to preserve other settings
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            console.print(f"[red]Warning: Could not read existing config file. Overwriting.[/red]")

    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)

    config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY] = api_key

    # Ensure the configuration directory exists
    config_dir = get_config_dir_path()
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"API Key saved to {config_file}", style="green")
    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e

def get_default_output_style() -> Literal["auto", "tui", "inline"]:
    """Gets the default output style from the configuration file."""
    config_file = get_config_file_path()
    if config_file.exists():
        config = configparser.ConfigParser()
        try:
            config.read(config_file)
            if SETTINGS_SECTION in config and OUTPUT_STYLE_CONFIG_KEY in config[SETTINGS_SECTION]:
                style = config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
                if style in get_args(Literal["auto", "tui", "inline"]):
                    return style
                else:
                    console.print(f"[yellow]Warning: Invalid output style '{style}' in config file. Using default.[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error reading configuration file {config_file}: {e}. Using default.[/yellow]")
    return DEFAULT_OUTPUT_STYLE


def set_default_output_style(style: str) -> None:
    """Sets the default output style in the configuration file."""
    if style not in get_args(Literal["auto", "tui", "inline"]):
        raise ValueError(f"Invalid output style: {style}. Must be one of 'auto', 'tui', or 'inline'.")

    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    # Read existing config if it exists, to preserve other settings
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            console.print(f"[red]Warning: Could not read existing config file. Overwriting.[/red]")

    if not config.has_section(SETTINGS_SECTION):
        config.add_section(SETTINGS_SECTION)

    config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY] = style

    # Ensure the configuration directory exists
    config_dir = get_config_dir_path()
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"Default output style saved to {config_file}", style="green")
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