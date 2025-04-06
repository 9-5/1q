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
    """Executes a shell command."""
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=False)
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] Command failed with exit code {result.returncode}")
            console.print(result.stderr)
    except FileNotFoundError:
        console.print("[red]Error:[/red] Command not found.  Is it installed and in your PATH?")
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="1Q - The right one-liner is just one query away.")
    parser.add_argument("query", nargs="?", help="The query to convert to a command.")
    parser.add_argument("-c", "--clear-history", action="store_true", help="Clear the history of queries and commands.")
    parser.add_argument("-s", "--set-default-output", dest="output_style", choices=get_args(config.VALID_OUTPUT_STYLES), help="Set and save the default output style in the config default.")
    parser.add_argument("-v", "--version", action="version", version="1.0.0") # TODO: Pull from pyproject.toml
    config_group = parser.add_argument_group("Configuration and Info Actions")
    config_group.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    config_group.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")
    config_group.add_argument("--set-default-output", dest="output_style", choices=get_args(config.VALID_OUTPUT_STYLES), help="Set and save the default output style in the config file (auto, tui, inline).")

    args = parser.parse_args()

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to clear the configuration file? This action cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.output_style:
         try:
              config.set_config_value(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, args.output_style)
              console.print(f"Default output style set to '{args.output_style}'.", style="green")
         except ConfigurationError as e:
              console.print(f"[red]Error:[/red] {e}", style="red")
         sys.exit(0)

    if args.clear_history:
         if Confirm.ask("Are you sure you want to clear the history file? This action cannot be undone."):
              history.clear_history_file()
         sys.exit(0)


    try:
        api_key = config.get_gemini_api_key()
    except ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found.[/yellow]")
        try:
            api_key = tui.run_api_key_setup()
            if api_key is None:
                raise ApiKeySetupCancelled("API key setup cancelled.")
            config.save_gemini_api_key(api_key)
            console.print("[green]Gemini API key saved successfully![/green]")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] Failed to save API key: {e}", style="red")
            sys.exit(1)


    if not args.query:
        console.print("No query provided. Please provide a query to convert to a command.", style="yellow")
        sys.exit(1)

    try:
        command = gemini.generate_command(args.query, api_key)
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
        sys.exit(1)

    output_style = config.get_output_style()

    if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
        try:
            response_data = {"query": args.query, "command": command}
            result = tui.display_response_tui(response_data)

            if result == "execute":
                execute_command(command)
                history.save_history(args.query, command)
            elif result == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard![/green]")
                    history.save_history(args.query, command)
                else:
                     console.print("[red]Error:[/red] pyperclip is not installed. Please install it to copy to clipboard.")
            elif result == "modify":
                 # Allow the user to modify the command
                 modified_command = Prompt.ask("Enter the modified command", default=command)
                 execute_command(modified_command)
                 history.save_history(args.query, modified_command) # Save modified command
            elif result == "refine":
                 # Re-run the query with a refined version
                 refined_query = Prompt.ask("Enter a refined query", default=args.query)
                 # TODO: Rerun the gemini command and display results.  For now just exit
                 try:
                      new_command = gemini.generate_command(refined_query, api_key)
                      response_data = {"query": refined_query, "command": new_command}
                      result = tui.display_response_tui(response_data)

                      if result == "execute":
                           execute_command(new_command)
                           history.save_history(refined_query, new_command)
                      elif result == "copy":
                           if PYPERCLIP_AVAILABLE:
                                pyperclip.copy(new_command)
                                console.print("[green]Command copied to clipboard![/green]")
                                history.save_history(refined_query, new_command)
                           else:
                                console.print("[red]Error:[/red] pyperclip is not installed. Please install it to copy to clipboard.")
                      elif result == "modify":
                           modified_command = Prompt.ask("Enter the modified command", default=new_command)
                           execute_command(modified_command)
                           history.save_history(refined_query, modified_command)
                 except GeminiApiError as e:
                      console.print(f"[red]Gemini API Error:[/red] {e}", style="red")

        except Exception as e:
            console.print(f"[red]TUI Error:[/red] An error occurred in the TUI: {e}", style="red")

    else:  # Inline output
        console.print(f"Generated Command: [cyan]{command}[/cyan]")
        if PYPERCLIP_AVAILABLE:
            if Confirm.ask("Copy command to clipboard?"):
                pyperclip.copy(command)
                console.print("[green]Command copied to clipboard![/green]")
                history.save_history(args.query, command)
        else:
            console.print("[yellow]pyperclip not installed. Install it to copy commands to clipboard.[/yellow]")
            history.save_history(args.query, command)

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
        import oneq_cli.history as history # Import history module
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()