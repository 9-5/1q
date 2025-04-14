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
    """Executes a shell command using subprocess."""
    try:
        console.print(f"Executing: [bold blue]{command}[/]")
        # Use shlex.split to correctly handle quoted arguments
        command_list = shlex.split(command)
        result = subprocess.run(command_list, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            console.print(f"[green]Command executed successfully.[/]")
            if result.stdout:
                console.print(f"[bold]Output:[/]\n{result.stdout}")
        else:
            console.print(f"[red]Command failed with code {result.returncode}.[/]")
            if result.stderr:
                console.print(f"[bold]Error:[/]\n{result.stderr}")
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Command not found: {command_list[0]}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error:[/red] Command execution failed: {e}")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/]")

def copy_to_clipboard(text: str) -> bool:
    """Copies the given text to the clipboard.
    Returns True on success, False otherwise."""
    if not PYPERCLIP_AVAILABLE:
        console.print("[yellow]pyperclip is not installed. Cannot copy to clipboard.[/]")
        return False
    try:
        pyperclip.copy(text)
        console.print("[green]Command copied to clipboard![/]")
        return True
    except pyperclip.PyperclipException as e:
        console.print(f"[red]Failed to copy to clipboard: {e}[/]")
        return False

def main() -> None:
    """
    Main entry point for the 1Q CLI.
    """
    # Check if running as a standalone script
    if __name__ == "__main__":
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


    parser = argparse.ArgumentParser(description="1Q: Get the right one-liner with one query.")
    parser.add_argument("query", nargs="?", help="The query to generate a command for.")
    parser.add_argument("-o", "--output", type=str, choices=get_args(config.VALID_OUTPUT_STYLES),
                        help="Force a specific output style (auto, tui, inline). Overrides config setting.",
                        default=None) # Set default to None to differentiate from config default.
    parser.add_argument("-v", "--version", action="version", version="1Q 1.0.0")
    parser.add_argument("--show-config-path", action="store_true",
                        help="Print the path to the configuration file and exit.")
    parser.add_argument("--clear-config", action="store_true",
                        help="Remove the configuration file (prompts for confirmation).")
    parser.add_argument("--set-default-output", type=str, choices=get_args(config.VALID_OUTPUT_STYLES),
                        help="Set and save the default output style in the config file (auto, tui, inline).")

    args = parser.parse_args()

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        sys.exit(0)

    if args.set_default_output:
        try:
            config.set_config_value(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, args.set_default_output)
            console.print(f"Default output style set to '{args.set_default_output}'.", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error setting default output style: {e}[/]", style="red")
        sys.exit(0)


    # Load configuration
    try:
        cfg = config.load_config()
        api_key = cfg.get(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY)
        default_output_style = cfg.get(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, fallback=config.DEFAULT_OUTPUT_STYLE)
    except config.ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found. Please set it up.[/]")
        api_key = None # Ensure api_key is None for the TUI.
    except config.ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/]", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error loading configuration: {e}[/]", style="red")
        sys.exit(1)


    # Handle missing API key
    if not api_key:
        if args.output == "inline":
            console.print("[red]API key is required for inline output. Please configure it.[/]")
            sys.exit(1)

        try:
            api_key = tui.ApiKeyApp.run() # type: ignore # It returns Union[str, None]
            if api_key is None:
                raise ApiKeySetupCancelled("API key setup cancelled.")
            config.set_config_value(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY, api_key)
            console.print("[green]API key saved successfully![/]")

        except ApiKeySetupCancelled:
            console.print("[yellow]API key setup cancelled.[/]")
            sys.exit(1)
        except ConfigurationError as e:
            console.print(f"[red]Error saving API key: {e}[/]", style="red")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error during API key setup: {e}[/]", style="red")
            sys.exit(1)


    # Determine output style
    output_style = args.output or default_output_style # CLI arg overrides config.
    if output_style == "auto":
        output_style = "tui" if sys.stdout.isatty() else "inline" # type: ignore # it's either "tui" or "inline"



    # Process query
    if args.query:
        try:
            response = gemini.generate_command(api_key, args.query)
            if response:
                command = response.get("command", "")
                explanation = response.get("explanation", "")

                if output_style == "inline":
                    console.print(f"[bold blue]Command:[/]\n{command}\n")
                    console.print(f"[bold]Explanation:[/]\n{explanation}")
                    config.save_history(args.query, command)

                elif output_style == "tui":
                    response_data = {"query": args.query, "command": command, "explanation": explanation}
                    tui_result = tui.display_response_tui(response_data)

                    if tui_result == "execute":
                        execute_command(command)
                        config.save_history(args.query, command)
                    elif tui_result == "modify":
                        console.print("[yellow]Command modification not yet implemented.[/]")
                    elif tui_result == "refine":
                         console.print("[yellow]Query refinement not yet implemented.[/]")
                    elif tui_result == "copy":
                        config.save_history(args.query, command)
                        copy_to_clipboard(command) # Copy regardless of execution

        except GeminiApiError as e:
            console.print(f"[red]Gemini API Error: {e}[/]", style="red")
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/]", style="red")
    else:
        parser.print_help()


    # Exit cleanly (important for Textual TUI apps)
    sys.exit(0)

if __name__ == "__main__":
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