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

console = Console(stderr=True)

def main() -> None:
    """Main entry point for the 1q CLI."""
    parser = argparse.ArgumentParser(
        description="1Q - The right one-liner is just one query away.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("query", nargs="?", help="The query to translate into a command.")
    parser.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config",
        action="store_true",
        help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output",
        dest="output_style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )
    parser.add_argument("-v", "--version", action="store_true", help="show program's version number and exit")
    args = parser.parse_args()

    if args.version:
        from importlib.metadata import version
        print(f"1q version: {version('oneq')}")
        sys.exit(0)

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file? This cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.output_style:
        try:
            config.save_output_style(args.output_style)
            console.print(f"Default output style set to: {args.output_style}", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    # Normal operation: process the query
    query = args.query

    try:
        api_key = config.get_api_key()
    except config.ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found.[/yellow]")
        console.print("Opening a TUI to guide you through the setup...", style="blue")
        try:
            api_key = tui.ApiKeyApp.run()
            if api_key:
                config.save_api_key(api_key)
                console.print("[green]API key saved successfully![/green]")
            else:
                raise ApiKeySetupCancelled("No API key was provided through the TUI.")

        except ApiKeySetupCancelled:
            console.print("[red]API Key setup cancelled.[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]An unexpected error occurred during API key setup: {e}[/red]")
            sys.exit(1)

    if not query:
        console.print("Enter your query, or use --help for options.")
        sys.exit(0)

    try:
        response = gemini.generate_command(query, api_key)
        output_style = config.get_output_style()

        if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
            from .tui import display_response_tui
            tui_result = display_response_tui(response)

            if tui_result.action == "execute":
                command_to_execute = tui_result.command_text
                if command_to_execute:
                    try:
                        console.print(f"Executing: [cyan]{command_to_execute}[/cyan]")
                        # Execute the command using subprocess
                        process = subprocess.Popen(shlex.split(command_to_execute),
                                                stdout=sys.stdout,
                                                stderr=sys.stderr,
                                                cwd=os.getcwd()) # Use current working directory
                        process.wait() # Wait for the process to complete
                    except FileNotFoundError as e:
                        console.print(f"[red]Error: Command not found: {e}[/red]")
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error: Command failed with return code {e.returncode}: {e.stderr.decode()}[/red]")
                    except Exception as e:
                        console.print(f"[red]An unexpected error occurred during command execution: {e}[/red]")

            elif tui_result.action == "modify":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(tui_result.command_text)
                    console.print("[green]Command copied to clipboard. Modify as needed.[/green]")
                else:
                    console.print(f"[yellow]Command:[/yellow] {tui_result.command_text}")
                    console.print("[yellow]pyperclip not installed. Please install it to copy commands to the clipboard.[/yellow]")

            elif tui_result.action == "refine":
                console.print("[yellow]Refine query feature not yet implemented.[/yellow]") # To implement later

        else: # Inline mode
            console.print(f"[bold]Command:[/bold] {response.get('command', 'No command generated.')}")
            console.print(f"[bold]Explanation:[/bold] {response.get('explanation', 'No explanation provided.')}")

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
    except ApiKeyNotFound:
        console.print("[red]API key not found. Please configure using --set-api-key or set the GEMINI_API_KEY environment variable.[/red]", style="red")
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
    except OneQError as e:
        console.print(f"[red]An error occurred:[/red] {e}", style="red")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {e}", style="red")


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