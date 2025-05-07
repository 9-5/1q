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

console = Console(stderr=True)

def _get_config_dir() -> Path:
    """Gets the OS-agnostic user config directory for 1Q, ensuring it exists."""
    return user_config_path(appname=CONFIG_DIR_NAME, ensure_exists=True)

def get_config_file_path() -> Path:
    """Gets the full path to the configuration file."""
    return _get_config_dir() / CONFIG_FILE_NAME

def load_api_key() -> str:
    """
    Loads the Gemini API key.
    Checks Environment Variable (GEMINI_API_KEY) first, then config file.

    Raises:
        ApiKeyNotFound: If the API key is not found.
        ConfigurationError: If there's an issue reading the config file.

    Returns:
        The loaded API key.
    """
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    config_file = get_config_file_path()
    if config_file.exists():
        try:
            parser = configparser.ConfigParser()
            parser.read(config_file)
            if CREDENTIALS_SECTION in parser and API_KEY_CONFIG_KEY in parser[CREDENTIALS_SECTION]:
                key_from_file = parser[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
                if key_from_file:
                    return key_from_file
                else:
                     console.print(f"[yellow]Warning:[/yellow] Found config file but API key is empty: {config_file}", style="yellow")

        except configparser.Error as e:
            raise ConfigurationError(f"Error reading configuration file {config_file}: {e}") from e
        except Exception as e:
             raise ConfigurationError(f"Unexpected error reading configuration file {config_file}: {e}") from e

    raise ApiKeyNotFound("Gemini API key not found. Set GEMINI_API_KEY environment variable or run `1q` to configure.")


def load_output_style() -> VALID_OUTPUT_STYLES:
    """
    Loads the preferred output style from the configuration file.

    Returns:
        The output style ('auto', 'tui', or 'inline'). Defaults to 'auto'.
    """
    config_file = get_config_file_path()
    if config_file.exists():
        try:
            parser = configparser.ConfigParser()
            parser.read(config_file)
            if SETTINGS_SECTION in parser and OUTPUT_STYLE_CONFIG_KEY in parser[SETTINGS_SECTION]:
                style = parser[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY].lower()
                if style in get_args(VALID_OUTPUT_STYLES):
                    return style # type: ignore
                else:
                    console.print(f"[yellow]Warning:[/yellow] Invalid output_style '{style}' in config. Using default '{DEFAULT_OUTPUT_STYLE}'.", style="yellow")
        except configparser.Error as e:
             console.print(f"[yellow]Warning:[/yellow] Error reading output_style from {config_file}: {e}. Using default '{DEFAULT_OUTPUT_STYLE}'.", style="yellow")
        except Exception as e:
             console.print(f"[yellow]Warning:[/yellow] Unexpected error reading output_style from {config_file}: {e}. Using default '{DEFAULT_OUTPUT_STYLE}'.", style="yellow")

    return DEFAULT_OUTPUT_STYLE

def save_api_key(api_key: str) -> None:
    """
    Saves the Gemini API key to the configuration file.

    Args:
        api_key: The API key string to save.

    Raises:
        ConfigurationError: If there's an issue writing the config file.
        ValueError: If the API key is empty.
    """
    if not api_key:
        raise ValueError("Attempted to save an empty API key.")

    config_dir = _get_config_dir()
    config_file = get_config_file_path()

    parser = configparser.ConfigParser()
    if config_file.exists():
        try:
            parser.read(config_file)
        except configparser.Error as e:
             console.print(f"[yellow]Warning:[/yellow] Could not read existing config file at {config_file}, it might be overwritten. Error: {e}", style="yellow")

    if CREDENTIALS_SECTION not in parser:
        parser.add_section(CREDENTIALS_SECTION)

    parser[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY] = api_key

    try:
        with open(config_file, 'w') as f:
            parser.write(f)
        if sys.platform != "win32":
             try:
                 os.chmod(config_file, 0o600) # Read/write for owner only
             except OSError as e:
                  console.print(f"[yellow]Warning:[/yellow] Could not set file permissions on {config_file}: {e}", style="yellow")
    except IOError as e:
        raise ConfigurationError(f"Error writing configuration file {config_file}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error writing configuration file {config_file}: {e}") from e

def save_output_style(style: VALID_OUTPUT_STYLES) -> None:
    """
    Saves the output style preference to the configuration file.

    Args:
        style: The output style ('auto', 'tui', or 'inline').

    Raises:
        ConfigurationError: If there's an issue writing the config file.
        ValueError: If the style is invalid.
    """
    if style not in get_args(VALID_OUTPUT_STYLES):
         raise ValueError(f"Invalid output style '{style}'. Must be one of {get_args(VALID_OUTPUT_STYLES)}.")

    config_dir = _get_config_dir()
    config_file = get_config_file_path()
    parser = configparser.ConfigParser()

    if config_file.exists():
        try:
            parser.read(config_file)
        except configparser.Error as e:
             console.print(f"[yellow]Warning:[/yellow] Could not read existing config file at {config_file}, it might be overwritten. Error: {e}", style="yellow")

    if SETTINGS_SECTION not in parser:
        parser.add_section(SETTINGS_SECTION)

    parser[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY] = style

    try:
        with open(config_file, 'w') as f:
            parser.write(f)
        if sys.platform != "win32":
             try:
                 os.chmod(config_file, 0o600)
             except OSError as e:
                  console.print(f"[yellow]Warning:[/yellow] Could not set file permissions on {config_file}: {e}", style="yellow")
        # Print confirmation (useful for --set-default-output flag)
        console.print(f"Default output style set to '{style}' in: {config_file}", style="green")
    except IOError as e:
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