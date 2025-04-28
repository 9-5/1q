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

def get_config_dir_path() -> Path:
    """Returns the path to the application's configuration directory."""
    return Path(user_config_path(APP_NAME, appauthor=False))

def get_config_file_path() -> Path:
    """Returns the path to the configuration file."""
    return get_config_dir_path() / CONFIG_FILE_NAME

def get_api_key() -> str:
    """
    Retrieves the Gemini API key from the environment variables or the configuration file.

    Returns:
        str: The Gemini API key.

    Raises:
        ApiKeyNotFound: If the API key is not found in either the environment variables or the configuration file.
        ConfigurationError: If there's an issue reading the configuration file.
    """
    # 1. Check environment variables
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    # 2. Check the configuration file
    config_file = get_config_file_path()
    if config_file.exists():
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            if CREDENTIALS_SECTION in config and API_KEY_CONFIG_KEY in config[CREDENTIALS_SECTION]:
                return config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
        except Exception as e:
            raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e

    # 3. If not found anywhere, raise ApiKeyNotFound
    raise ApiKeyNotFound("Gemini API key not found. Please set the GEMINI_API_KEY environment variable or configure it using --set-api-key.")

def get_output_style() -> VALID_OUTPUT_STYLES:
    """
    Retrieves the configured output style from the configuration file.  Defaults to "auto".
    """
    config_file = get_config_file_path()
    if config_file.exists():
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            if SETTINGS_SECTION in config and OUTPUT_STYLE_CONFIG_KEY in config[SETTINGS_SECTION]:
                output_style = config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
                if output_style in get_args(VALID_OUTPUT_STYLES):
                    return output_style # type: ignore
                else:
                    console.print(f"[yellow]Warning:[/yellow] Invalid output style '{output_style}' in config file. Falling back to default 'auto'.", style="yellow")
                    return DEFAULT_OUTPUT_STYLE
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error reading configuration file {config_file}. Falling back to default 'auto'.", style="yellow")
            return DEFAULT_OUTPUT_STYLE
    return DEFAULT_OUTPUT_STYLE


def save_api_key(api_key: str) -> None:
    """
    Saves the Gemini API key to the configuration file.

    Args:
        api_key (str): The Gemini API key to save.

    Raises:
        ConfigurationError: If there's an issue writing to the configuration file.
    """
    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    # Read existing config if it exists, to preserve other settings
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error reading existing configuration file {config_file}.  Existing settings may be lost.", style="yellow")

    if not config.has_section(CREDENTIALS_SECTION):
        config.add_section(CREDENTIALS_SECTION)
    config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY] = api_key

    try:
        # Ensure the config directory exists
        config_dir = get_config_dir_path()
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
        os.chmod(config_file, 0o600)  # Set permissions to read/write for the user only

        console.print(f"API key saved to {config_file}", style="green")
    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e

def set_output_style(output_style: str) -> None:
    """
    Sets the default output style in the configuration file.

    Args:
        output_style (str): The output style to set (tui, inline, auto).

    Raises:
        ValueError: If the provided output style is invalid.
        ConfigurationError: If there's an issue writing to the configuration file.
    """
    if output_style not in get_args(VALID_OUTPUT_STYLES):
        raise ValueError(f"Invalid output style: {output_style}.  Must be one of {get_args(VALID_OUTPUT_STYLES)}")

    config_file = get_config_file_path()
    config = configparser.ConfigParser()

    # Read existing config if it exists
    if config_file.exists():
        try:
            config.read(config_file)
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error reading existing configuration file {config_file}. Existing settings may be lost.", style="yellow")

    if not config.has_section(SETTINGS_SECTION):
        config.add_section(SETTINGS_SECTION)
    config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY] = output_style

    try:
        # Ensure the config directory exists
        config_dir = get_config_dir_path()
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            config.write(f)
        os.chmod(config_file, 0o600)  # Set permissions to read/write for the user only
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