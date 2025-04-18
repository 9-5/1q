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


def get_gemini_api_key() -> str:
    """
    Retrieves the Gemini API key from the environment variables or the configuration file.

    Returns:
        str: The Gemini API key.

    Raises:
        ApiKeyNotFound: If the API key is not found in either the environment variables or the configuration file.
    """
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if api_key:
        return api_key

    config_file = get_config_file_path()
    if config_file.exists():
        config = configparser.ConfigParser()
        config.read(config_file)
        try:
            return config[CREDENTIALS_SECTION][API_KEY_CONFIG_KEY]
        except KeyError:
            pass  # Key not found in config file

    raise ApiKeyNotFound(
        f"Gemini API key not found. Please set the {API_KEY_ENV_VAR} environment variable or configure it via the TUI."
    )


class ConfigManager:
    """Manages reading, writing, and updating the configuration file."""

    def __init__(self) -> None:
        self.config_file = get_config_file_path()
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

        # Ensure sections exist
        if not self.config.has_section(CREDENTIALS_SECTION):
            self.config.add_section(CREDENTIALS_SECTION)
        if not self.config.has_section(SETTINGS_SECTION):
            self.config.add_section(SETTINGS_SECTION)

    def get_output_style(self) -> str:
        """Gets the configured output style, defaulting to 'auto' if not set."""
        try:
            style = self.config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY]
            if style not in get_args(VALID_OUTPUT_STYLES):
                console.print(f"[yellow]Invalid output style in config file: {style}.  Using default 'auto'.[/]")
                return DEFAULT_OUTPUT_STYLE
            return style
        except KeyError:
            return DEFAULT_OUTPUT_STYLE

    def set_output_style(self, style: str) -> None:
        """Sets the output style in the configuration."""
        if style not in get_args(VALID_OUTPUT_STYLES):
            raise ValueError(f"Invalid output style: {style}")
        self.config[SETTINGS_SECTION][OUTPUT_STYLE_CONFIG_KEY] = style

    def save_config(self) -> None:
        """Writes the configuration to the config file."""
        try:
            # Ensure the config directory exists
            config_dir = self.config_file.parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w") as f:
                self.config.write(f)
        except OSError as e:
            raise ConfigurationError(f"Error writing configuration file {self.config_file}: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Unexpected error writing configuration file {self.config_file}: {e}") from e


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