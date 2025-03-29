# D:\1q\src\oneq_cli\cli.py
import argparse
import sys
import os
import re
import subprocess
import shlex
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Literal

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text

from . import config
from . import gemini
from . import tui
from .exceptions import (
    ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
)

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    from typing import get_args
except ImportError:
    # Basic fallback for Python < 3.8
    def get_args(tp):
        return getattr(tp, '__args__', ())

console = Console()

def execute_command(command: str) -> None:
    """
    Executes a given command using subprocess.
    """
    try:
        # Use shlex.split to handle quoted arguments correctly
        command_list = shlex.split(command)
        result = subprocess.run(command_list, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] Command failed with return code {result.returncode}", style="red")
            console.print(result.stderr, style="red")

    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Command not found: {command}", style="red")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error:[/red] Command '{e.cmd}' failed with return code {e.returncode}", style="red")
        console.print(e.output, style="red")
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {e}", style="red")


def main() -> None:
    """
    Main entry point for the 1Q CLI application.
    """
    parser = argparse.ArgumentParser(
        description="1Q: 1 query away from the right one-line command.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("query", nargs="?", help="The query to convert into a command.")
    parser.add_argument("-k", "--api-key", dest="api_key", help="Set the Gemini API key. Overrides config default.")
    parser.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    parser.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")
    parser.add_argument(
        "--set-default-output",
        dest="output_style",
        choices=get_args(Literal["auto", "tui", "inline"]),
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument("-v", "--version", action="version", version="1.0.0") # TODO: load from pyproject.toml
    args = parser.parse_args()

    # Handle config actions first as they may exit the program
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file? This action cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.output_style:
        try:
            config.set_output_style(args.output_style)
            console.print(f"Default output style set to '{args.output_style}'.", style="green")
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    # Load configuration
    try:
        cfg = config.load_config()
    except FileNotFoundError:
        cfg = {}  # Use an empty dictionary if the config file doesn't exist
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
        sys.exit(1)

    # Determine API key source
    api_key = args.api_key or cfg.get(config.CREDENTIALS_SECTION, {}).get(config.API_KEY_CONFIG_KEY) or os.environ.get(config.API_KEY_ENV_VAR)

    # If API key is still not found, attempt to get it via TUI
    if not api_key:
        console.print("[yellow]Gemini API key not found.[/yellow]", style="yellow")
        try:
            api_key = tui.ApiKeyApp.run()
            if api_key:
                config.save_api_key(api_key)
                console.print("[green]API key saved successfully![/green]", style="green")
            else:
                raise ApiKeySetupCancelled("API key setup cancelled.")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] Could not save API key: {e}", style="red")
            sys.exit(1)

    # Initialize Gemini
    try:
        gemini.init_gemini(api_key)
    except ApiKeyNotFound as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)

    # Handle no query provided
    query = args.query
    if not query:
        query = Prompt.ask("Enter your query")

    # Determine output style
    output_style = cfg.get(config.SETTINGS_SECTION, {}).get(config.OUTPUT_STYLE_CONFIG_KEY, config.DEFAULT_OUTPUT_STYLE)
    if output_style == "auto":
        output_style = "tui" if sys.stdout.isatty() else "inline" # TODO: add better auto-detection

    # Generate and display the command
    try:
        response_data = gemini.generate_command(query)
        if output_style == "tui":
            result = tui.display_response_tui(response_data)

            if result == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(response_data["command"])
                    console.print("[green]Command copied to clipboard![/green]", style="green")
                else:
                    console.print("[yellow]pyperclip not installed. Please install it to use the copy functionality.[/yellow]", style="yellow")
            elif result == "execute":
                execute_command(response_data["command"])
            elif result == "modify":
                new_command = Prompt.ask("Enter the modified command", default=response_data["command"])
                execute_command(new_command)
            elif result == "refine":
                new_query = Prompt.ask("Enter a more specific query based on the last one", default=query)
                # Recursively call main with the new query.  This may need revisiting.
                # Create a new parser to avoid conflicts with existing args.
                new_args = parser.parse_args([new_query])
                args.query = new_args.query
                main() #Potential recursion issue, but simplest for now
            elif result is None:
                pass # User quit the TUI
            else:
                console.print(f"[red]Unknown action: {result}[/red]", style="red")
        else:  # inline
            console.print(response_data["command"])

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
    except Exception as e:
        console.print(f"[red]Unexpected Error:[/red] {e}", style="red")


# Execute CLI if run as a script
if __name__ == "__main__":
    # Add src/ to path when running from the project root, but not when installed
    # Check if running from project root

    #This block is needed when running the script from the project directory,
    #but causes a double import when installed as a package.
    #See: https://stackoverflow.com/questions/56974444/importerror-attempted-relative-import-beyond-top-level-package
    project_root = Path(__file__).resolve().parent.parent.parent
    src_path = project_root / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    try:
        import oneq_cli.config as cfg
        config = cfg
        import oneq_cli.gemini as gem
        gemini = gem
        import oneq_cli.tui as tui_mod
        tui = tui_mod
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()