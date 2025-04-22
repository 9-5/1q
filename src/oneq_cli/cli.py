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

def execute_command(command: str) -> None:
    """Executes a shell command."""
    try:
        # Using shlex.split to handle quoted arguments correctly
        args = shlex.split(command)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if stdout:
            console.print("STDOUT:\n", style="bold green")
            console.print(stdout.decode())
        if stderr:
            console.print("STDERR:\n", style="bold red")
            console.print(stderr.decode())

        if process.returncode != 0:
            console.print(f"Command failed with return code: {process.returncode}", style="bold red")

    except FileNotFoundError:
        console.print(f"Command not found: {command}", style="bold red")
    except Exception as e:
        console.print(f"Error executing command: {e}", style="bold red")

def main() -> None:
    """Main entry point for the 1q CLI."""
    parser = argparse.ArgumentParser(description="1Q: Get the right one-liner with one query.")
    parser.add_argument("query", nargs="?", help="The query to generate a command for.")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute the generated command directly.")
    parser.add_argument("-c", "--copy", action="store_true", help="Copy the generated command to the clipboard.")
    parser.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    parser.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")
    parser.add_argument("--set-default-output", type=str, choices=config.get_args(config.VALID_OUTPUT_STYLES), help="Set and save the default output style in the config file (auto, tui, inline).")
    parser.add_argument("-v", "--version", action="version", version="1Q 1.0.0")

    args = parser.parse_args()

    # Handle config related actions first
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file? This action cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.set_default_output:
        try:
            config.set_default_output_style(args.set_default_output)
            console.print(f"Default output style set to: {args.set_default_output}", style="green")
        except Exception as e:
            console.print(f"Error setting default output style: {e}", style="red")
        sys.exit(0)

    # Check for API key
    try:
        api_key = config.get_api_key()
    except ApiKeyNotFound:
        console.print("[bold yellow]Gemini API key not found.[/bold yellow]")
        if Confirm.ask("Do you want to set up the API key now using the TUI?"):
            try:
                api_key = tui.run_api_key_setup() # type: ignore
                if api_key:
                    console.print("[green]API key setup complete.[/green]")
                else:
                    console.print("[yellow]API key setup cancelled.[/yellow]")
                    sys.exit(1)
            except tui.ApiKeySetupCancelled:
                console.print("[yellow]API key setup cancelled.[/yellow]")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]Error during API key setup: {e}[/red]")
                sys.exit(1)
        else:
            console.print("Please set the GEMINI_API_KEY environment variable or run 1q with the TUI to configure it.", style="yellow")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error getting API key: {e}[/red]")
        sys.exit(1)


    if not args.query:
        console.print("Please provide a query.", style="bold yellow")
        sys.exit(1)

    try:
        response = gemini.generate_command(args.query, api_key) # type: ignore
        if response:
            command = response.get("command", "")
            if not command:
                console.print("[red]No command was generated.[/red]")
                sys.exit(1)

            output_style = config.get_default_output_style()

            if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
                # Launch TUI
                response_data = {"query": args.query, "command": command}
                tui_action = tui.display_response_tui(response_data)
                if tui_action == "execute":
                    execute_command(command)
                elif tui_action == "modify":
                    # For now, just print the command.  Future: Open in editor.
                    console.print("[bold yellow]Please manually modify the command:[/bold yellow]")
                    console.print(command)
                elif tui_action == "refine":
                    console.print("[bold yellow]Please refine your query and try again.[/bold yellow]")
                elif tui_action == "copy":
                    if PYPERCLIP_AVAILABLE:
                        pyperclip.copy(command)
                        console.print("[green]Command copied to clipboard![/green]")
                    else:
                         console.print("[red]pyperclip not available. Please install it to use the copy feature.[/red]")

            else: # inline or auto (when not a tty)
                console.print("Generated Command:", style="bold green")
                console.print(command)

                if args.execute:
                    execute_command(command)
                elif args.copy:
                    if PYPERCLIP_AVAILABLE:
                        pyperclip.copy(command)
                        console.print("[green]Command copied to clipboard![/green]")
                    else:
                        console.print("[red]pyperclip not available. Please install it to use the copy feature.[/red]")

            # Save history
            history.save_history(args.query, command)
        else:
            console.print("[red]Failed to generate command.[/red]")
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error: {e}[/red]")
    except OneQError as e:
        console.print(f"[red]Application Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")

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