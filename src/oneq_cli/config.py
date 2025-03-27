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


def get_api_key() -> str:
    """
    Retrieves the Gemini API key from environment variables or the configuration file.

    Raises:
        ApiKeyNotFound: If the API key is not found in either location.
        ConfigurationError: If there's an issue reading the configuration file.
    """
    # 1. Check environment variable
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    # 2. Check configuration file
    config_file = get_config_file_path()
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        if CREDENTIALS_SECTION in config and API_KEY_CONFIG_KEY in config[CREDENTIALS_SECTION]:
            return config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
    except Exception as e:
        raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e

    raise ApiKeyNotFound("Gemini API key not found in environment variables or configuration file.")


def save_api_key(api_key: str) -> None:
    """
    Saves the Gemini API key to the configuration file.

    Args:
        api_key: The Gemini API key to save.

    Raises:
        ConfigurationError: If there's an issue writing to the configuration file.
    """
    config_file = get_config_file_path()
    config_dir = config_file.parent
    config = configparser.ConfigParser()

    # Check if the configuration file exists and read it
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            raise ConfigurationError(f"Error reading existing configuration file {config_file}: {e}") from e

    # Add the credentials section if it doesn't exist
    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)

    # Set the API key in the credentials section
    config.set(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY, api_key)

    # Ensure the configuration directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write the configuration to the file
    try:
        with open(config_file, "w") as f:
            config.write(f)
        console.print(f"API Key saved to {config_file}", style="green")
    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e


def get_output_style() -> VALID_OUTPUT_STYLES:
    """
    Retrieves the output style from the configuration file.  Defaults to 'auto'.

    Returns:
        The configured output style ("auto", "tui", or "inline").
        If not found, returns the DEFAULT_OUTPUT_STYLE.

    Raises:
        ConfigurationError: If there's an issue reading the configuration file
                            or if the configured value is invalid.
    """
    config_file = get_config_file_path()
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        if SETTINGS_SECTION in config and OUTPUT_STYLE_CONFIG_KEY in config[SETTINGS_SECTION]:
            output_style = config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
            if output_style in get_args(VALID_OUTPUT_STYLES):
                return output_style
            else:
                console.print(f"[yellow]Invalid output style '{output_style}' in config file. Using default.[/yellow]", style="yellow")
                return DEFAULT_OUTPUT_STYLE
    except Exception as e:
        console.print(f"[yellow]Error reading config file {config_file}: {e}. Using default output style.[/yellow]", style="yellow")
        return DEFAULT_OUTPUT_STYLE
    return DEFAULT_OUTPUT_STYLE


def set_output_style(output_style: VALID_OUTPUT_STYLES) -> None:
    """
    Sets the output style in the configuration file.

    Args:
        output_style: The output style to set ("auto", "tui", or "inline").

    Raises:
        ConfigurationError: If there's an issue writing to the configuration file.
    """
    config_file = get_config_file_path()
    config_dir = config_file.parent
    config = configparser.ConfigParser()

    # Check if the configuration file exists and read it
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            raise ConfigurationError(f"Error reading existing configuration file {config_file}: {e}") from e

    # Add the settings section if it doesn't exist
    if not config.has_section(SETTINGS_SECTION):
        config.add_section(SETTINGS_SECTION)

    # Set the output style in the settings section
    config.set(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, output_style)

    # Ensure the configuration directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write the configuration to the file
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