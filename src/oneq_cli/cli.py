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
from .history import load_history
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

def execute_command(command: str, dry_run: bool = False) -> None:
    """Executes a shell command."""
    if dry_run:
        console.print(f"[green]Dry-run:[/green] Would execute: [bold]{command}[/bold]")
        return

    try:
        console.print(f"[green]Executing:[/green] [bold]{command}[/bold]")
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=False)

        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] Command failed with return code {result.returncode}")
            console.print(result.stderr)

    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Command not found: {command}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error:[/red] Command '{e.cmd}' returned non-zero exit status {e.returncode}.\n{e.stderr}")
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {e}")

def process_query(
    query: str,
    config: Any,
    output_style: str = "auto",
    dry_run: bool = False
) -> None:
    """
    Processes the user's query, interacts with the Gemini model, and handles the response.
    """
    try:
        api_key = config.get_api_key()
        if not api_key:
            raise ApiKeyNotFound("Gemini API key not found. Please set it using --configure or set the GEMINI_API_KEY environment variable.")

        response = gemini.generate_command(query, api_key)
        if not response:
            console.print("[yellow]No response received from the model.[/yellow]")
            return

        # Handle the response based on the configured output style
        if output_style == "auto":
            output_style = config.get_default_output_style() #Respect config default if auto

        if output_style == "tui":
            # Launch TUI
            response_data = {"query": query, "command": response}
            tui_action = tui.display_response_tui(response_data)

            if tui_action == "execute":
                execute_command(response, dry_run)
                # Save to history if executed
                from .history import save_history
                save_history(query, response) # Save the original response
            elif tui_action == "modify":
                modified_command = Prompt.ask("Enter the modified command", default=response)
                execute_command(modified_command, dry_run)
                # Save the modified command to history
                from .history import save_history
                save_history(query, modified_command) # Save the modified response
            elif tui_action == "refine":
                console.print("Refine query selected. Please run 1q with the refined query.")
            elif tui_action == "copy":
                 if PYPERCLIP_AVAILABLE:
                     pyperclip.copy(response)
                     console.print("[green]Command copied to clipboard![/green]")
                 else:
                     console.print("[yellow]pyperclip not installed. Please install it to use the copy feature.[/yellow]")

        elif output_style == "inline":
            # Print command inline with options to execute or copy
            console.print(f"\n[bold]Command:[/bold] {response}\n")

            action = Prompt.ask(
                "Choose an action: (e)xecute, (m)odify, (c)opy, or (q)uit",
                choices=["e", "m", "c", "q"],
                default="q"
            )

            if action == "e":
                execute_command(response, dry_run)
                 # Save to history if executed
                from .history import save_history
                save_history(query, response) # Save the original response
            elif action == "m":
                modified_command = Prompt.ask("Enter the modified command", default=response)
                execute_command(modified_command, dry_run)
                # Save the modified command to history
                from .history import save_history
                save_history(query, modified_command)  # Save the modified response
            elif action == "c":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(response)
                    console.print("[green]Command copied to clipboard![/green]")
                else:
                    console.print("[yellow]pyperclip not installed. Please install it to use the copy feature.[/yellow]")
            else:
                console.print("Quitting.")
        else:
            console.print(f"[red]Error:[/red] Invalid output style: {output_style}")

    except ApiKeyNotFound as e:
        console.print(f"[red]Error:[/red] {e}")
        if Confirm.ask("Do you want to configure the API key now?", default=True):
            try:
                config.configure_api_key_tui()
            except ApiKeySetupCancelled:
                console.print("API key setup cancelled.")
            except Exception as e:
                 console.print(f"[red]Error:[/red] An unexpected error occurred during API key setup: {e}")

    except GeminiApiError as e:
        console.print(f"[red]Error:[/red] Gemini API error: {e}")
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] Configuration error: {e}")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="1Q: Generate shell commands from natural language queries.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="The natural language query to translate into a command.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Print the command that would be executed, but don't execute it.")
    parser.add_argument(
        "--show-config-path", action="store_true", help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output",
        dest="output_style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )
    parser.add_argument(
        "-v", "--version", action="version", version="1Q version 1.0.0"
    )
    config_group = parser.add_argument_group("Configuration and Info Actions")

    # Mutually exclusive group for configure and clear-config
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--configure", action="store_true", help="Configure the Gemini API key using a TUI."
    )

    args = parser.parse_args()

    # Initialize configuration
    try:
        config_instance = config.Config()
    except config.ConfigurationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]", file=sys.stderr)
        sys.exit(1)

    if args.show_config_path:
        print(config_instance.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("[bold red]Are you sure you want to remove the configuration file?[/]", default=False):
            config.clear_config_file()
        else:
            console.print("Clear config cancelled.")
        sys.exit(0)

    if args.configure:
        try:
            config_instance.configure_api_key_tui()
        except ApiKeySetupCancelled:
            console.print("API key setup cancelled.")
        except Exception as e:
            console.print(f"[red]Error:[/red] An unexpected error occurred during API key setup: {e}")
        sys.exit(0)

    if args.output_style:
        try:
            config_instance.set_default_output_style(args.output_style)
            console.print(f"Default output style set to: {args.output_style}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(1)

    process_query(args.query, config_instance, dry_run=args.dry_run)

if __name__ == "__main__":
    # Add src/ to path when running from source
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