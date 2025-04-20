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
from .history import load_history, save_history
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

def generate_command(query: str) -> str:
    """Generates a command using the Gemini API."""
    try:
        api_key = config.get_api_key()
    except ApiKeyNotFound:
        console.print("[red]Error:[/red] Gemini API key not found. Please set it up using the TUI or environment variable.")
        raise

    try:
        command = gemini.generate_command(query, api_key)
        return command
    except GeminiApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise

def execute_command(command: str) -> None:
    """Executes a shell command."""
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=False)  # Changed check=True to check=False
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] Command failed with exit code {result.returncode}")
            console.print(result.stderr)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] Command not found: {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="1Q - The right one-liner is just one query away.")
    parser.add_argument("query", nargs="?", help="The query to convert into a command.")
    parser.add_argument("-c", "--copy", action="store_true", help="Copy the generated command to the clipboard.")
    parser.add_argument("-s", "--set-default-output", dest="style", choices=get_args(config.VALID_OUTPUT_STYLES), help="Set and save the default output style in the config file (auto, tui, inline).")
    parser.add_argument("-v", "--version", action="version", version="1.0.0") # type: ignore
    parser.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    parser.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")

    args = parser.parse_args()

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file? This action cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.style:
        try:
            config.set_default_output_style(args.style)
            console.print(f"Default output style set to '{args.style}'.", style="green")
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(0)

    try:
        default_output_style = config.get_default_output_style()
    except ConfigurationError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}.  Using 'auto' as default.")
        default_output_style = "auto"

    if not args.query:
        # Interactive mode or display help/examples
        console.print("Enter your query (or type 'exit' to quit):")
        while True:
            try:
                query = Prompt.ask("> ")
            except KeyboardInterrupt:
                print() # Print newline after Ctrl+C
                break

            if query.lower() == "exit":
                break

            args.query = query # Update args to use same logic as CLI mode
            process_query(args, default_output_style)

        sys.exit(0)

    process_query(args, default_output_style)

def process_query(args: argparse.Namespace, default_output_style: config.VALID_OUTPUT_STYLES) -> None:
    """Processes a single query based on CLI arguments and configuration."""
    query = args.query
    try:
        command = generate_command(query)
    except ApiKeyNotFound:
        # Launch TUI for API key setup if no API key is found
        api_key = tui.ApiKeyApp.run()
        if api_key:
            try:
                config.save_api_key(api_key)
                console.print("[green]Gemini API key saved successfully![/]")
                command = generate_command(query)  # Retry command generation
            except ConfigurationError as e:
                console.print(f"[red]Error:[/red] {e}")
                sys.exit(1)
        else:
            console.print("[yellow]API Key setup cancelled.[/]")
            sys.exit(1)
    except GeminiApiError:
        sys.exit(1) # Already reported in generate_command

    if default_output_style == "tui" or (default_output_style == "auto" and sys.stdout.isatty()):
        # Launch TUI
        response_data = {"query": query, "command": command}
        result = tui.display_response_tui(response_data)

        if result == "execute":
            execute_command(command)
            save_history(query, command)
        elif result == "modify":
            # Modify command logic would go here (future enhancement)
            console.print("[yellow]Command modification not yet implemented.[/]")
        elif result == "refine":
            # Refine query logic would go here (future enhancement)
            console.print("[yellow]Query refinement not yet implemented.[/]")
        elif result == "copy":
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard![/]")
                except pyperclip.PyperclipException:
                    console.print("[red]Error:[/red] Copy failed. Ensure you have 'xclip' or 'xsel' installed.")
            else:
                console.print("[red]Error:[/red] pyperclip is not installed. Please install it to use the copy feature.")

    else: # Inline output
        console.print(f"Query: {query}")
        console.print(f"Command: {command}")
        if args.copy:
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard![/]")
                except pyperclip.PyperclipException:
                    console.print("[red]Error:[/red] Copy failed. Ensure you have 'xclip' or 'xsel' installed.")
            else:
                console.print("[red]Error:[/red] pyperclip is not installed. Please install it to use the copy feature.")
        else:
             console.print("Use -c or --copy to copy to the clipboard.")
        execute_command(command)
        save_history(query, command)


if __name__ == "__main__":
    # Correctly resolve project root and add src/ to path for direct execution:
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