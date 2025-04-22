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

class ConfigManager:
    """Manages the application's configuration."""

    def __init__(self) -> None:
        self.config_file = Path(user_config_path(APP_NAME, appauthor=False)) / CONFIG_FILE_NAME
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

    def _get_config_value(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """Retrieves a configuration value from the config file."""
        try:
            return self.config[section][key]
        except KeyError:
            return fallback

    def _set_config_value(self, section: str, key: str, value: str) -> None:
        """Sets a configuration value in the config file."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def get_api_key(self) -> str:
        """Retrieves the Gemini API key from the environment or the config file."""
        api_key = os.environ.get(API_KEY_ENV_VAR)
        if not api_key:
            api_key = self._get_config_value(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY)
            if not api_key:
                raise ApiKeyNotFound("Gemini API key not found in environment or config file.")
        return api_key

    def save_api_key(self, api_key: str) -> None:
        """Saves the Gemini API key to the config file."""
        self._set_config_value(CREDENTIALS_SECTION, API_KEY_CONFIG_KEY, api_key)
        self._save_config()

    def get_default_output_style(self) -> VALID_OUTPUT_STYLES:
        """Gets the default output style from the config file."""
        style = self._get_config_value(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, DEFAULT_OUTPUT_STYLE)
        if style not in get_args(VALID_OUTPUT_STYLES):
            console.print(f"[yellow]Invalid output style in config file: {style}. Using default: {DEFAULT_OUTPUT_STYLE}[/yellow]")
            return DEFAULT_OUTPUT_STYLE
        return style # type: ignore[return-value]

    def set_default_output_style(self, style: VALID_OUTPUT_STYLES) -> None:
        """Sets the default output style in the config file."""
        self._set_config_value(SETTINGS_SECTION, OUTPUT_STYLE_CONFIG_KEY, style)
        self._save_config()

    def _save_config(self) -> None:
        """Saves the configuration to the config file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as configfile:
                self.config.write(configfile)
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

# Global config object
_config_manager = ConfigManager()

# Expose methods through the module-level interface, using the global instance.
get_api_key = _config_manager.get_api_key
save_api_key = _config_manager.save_api_key
get_default_output_style = _config_manager.get_default_output_style
set_default_output_style = _config_manager.set_default_output_style
get_config_file_path = _config_manager.config_file.__str__