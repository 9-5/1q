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


def main() -> None:
    # Monkey patch for local development
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

    parser = argparse.ArgumentParser(
        description="1Q: 1 query away from the right one-line command.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Main query argument
    parser.add_argument("query", nargs="?", help="The query to resolve into a command.")

    # Configuration and info actions (mutually exclusive)
    config_group = parser.add_argument_group("Configuration and Info Actions")
    config_group.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the path to the configuration file and exit."
    )
    config_group.add_argument(
        "--clear-config",
        action="store_true",
        help="Remove the configuration file (prompts for confirmation)."
    )
    config_group.add_argument(
        "--set-default-output",
        metavar="STYLE",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )

    # Other options
    parser.add_argument(
        "-v", "--version", action="version", version="1Q 1.0.0"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Bypass confirmation prompts."
    )

    args = parser.parse_args()

    # Handle configuration actions first (show path, clear config)
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if args.yes or Confirm.ask("[yellow]Are you sure you want to remove the configuration file?[/yellow]"):
            config.clear_config_file()
        else:
            console.print("Clear config cancelled.", style="yellow")
        sys.exit(0)

    if args.set_default_output:
        try:
            config.set_output_style(args.set_default_output)
            console.print(f"Default output style set to '{args.set_default_output}'.", style="green")
        except Exception as e:
            console.print(f"[red]Error:[/red] Could not set default output style: {e}", style="red")
        sys.exit(0)

    # Check for query (main operation)
    if not args.query:
        console.print("No query provided.  Example: 1q list files in Documents ending with .pdf", style="italic")
        sys.exit(1)

    try:
        api_key = config.get_api_key()
    except ApiKeyNotFound:
        console.print("[red]Error:[/red] Gemini API key not found.", style="red")
        if args.yes or Confirm.ask("[yellow]Do you want to set up the API key now?[/yellow]"):
            try:
                api_key = tui.get_gemini_api_key_from_tui()
                if api_key:
                    config.save_api_key(api_key)
                    console.print("[green]API key saved.[/green]", style="green")
                else:
                    raise ApiKeySetupCancelled("API key setup cancelled by user.")
            except ApiKeySetupCancelled as e:
                console.print(f"[yellow]API key setup cancelled: {e}[/yellow]", style="yellow")
                sys.exit(1)
        else:
            console.print("[yellow]Please set up the API key to use 1Q.[/yellow]", style="yellow")
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
        sys.exit(1)

    try:
        response_data = gemini.resolve_query(args.query, api_key=api_key)
        output_style = config.get_output_style()

        if output_style == "tui" or (output_style == "auto" and not sys.stdout.isatty()):
            result = tui.display_response_tui(response_data)

            if result == "execute":
                command_to_execute = response_data.get("command", None)
                if command_to_execute:
                     try:
                        console.print(f"Executing: {command_to_execute}")
                        subprocess.run(command_to_execute, shell=True, check=True) # nosec
                     except subprocess.CalledProcessError as e:
                         console.print(f"[red]Command failed:[/red] {e}", style="red")
                else:
                    console.print("[yellow]No command to execute.[/yellow]", style="yellow")

            elif result == "modify":
                command_to_modify = response_data.get("command", None)
                if command_to_modify:
                    modified_command = Prompt.ask("Modify command", default=command_to_modify)
                    console.print(f"Executing modified command: {modified_command}")
                    try:
                        subprocess.run(modified_command, shell=True, check=True) # nosec
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Command failed:[/red] {e}", style="red")
                else:
                    console.print("[yellow]No command to modify.[/yellow]", style="yellow")

            elif result == "refine":
                refined_query = Prompt.ask("Refine your query")
                # Re-run the query with the refined input (recursion or loop)
                new_response_data = gemini.resolve_query(refined_query, api_key=api_key)
                tui.display_response_tui(new_response_data) # or loop back to the start

            elif result == "copy":
                 if PYPERCLIP_AVAILABLE:
                    command_to_copy = response_data.get("command", None)
                    if command_to_copy:
                        pyperclip.copy(command_to_copy)
                        console.print("[green]Command copied to clipboard.[/green]", style="green")
                    else:
                        console.print("[yellow]No command to copy.[/yellow]", style="yellow")
                 else:
                     console.print("[yellow]pyperclip not available. Please install it to use the copy feature.[/yellow]", style="yellow")


        else:  # Inline output
            command_text = response_data.get("command", "No command generated.")
            explanation_text = response_data.get("explanation", "No explanation provided.")

            console.print(Text.assemble(
                ("\nCommand:\n", "bold"),
                (f"{command_text}\n", "cyan"),
                ("\nExplanation:\n", "bold"),
                f"{explanation_text}\n"
            ))

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
        sys.exit(1)
    except OneQError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)

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