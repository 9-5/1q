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

def execute_command(command: str, dry_run: bool = False) -> None:
    """Executes a shell command."""
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] {command}")
        return

    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=False)
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] Command failed with return code {result.returncode}")
            console.print(result.stderr)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Command not found: {command.split()[0]}")
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to execute command: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="1Q: Get the right one-liner with one query.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="Natural language query for the command.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Print the command without executing it.")
    parser.add_argument(
        "-o",
        "--output",
        choices=["auto", "tui", "inline"],
        help="Force output style (auto, tui, inline). Overrides config setting.",
    )
    parser.add_argument(
        "--show-config-path", action="store_true", help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output",
        choices=["auto", "tui", "inline"],
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument("-v", "--version", action="store_true", help="show program's version number and exit")

    args = parser.parse_args()

    if args.version:
        print("1Q version 1.0.0")
        sys.exit(0)

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        sys.exit(0)

    if args.set_default_output:
        try:
            config.set_output_style(args.set_default_output)
            console.print(
                f"Default output style set to '{args.set_default_output}' in config file.", style="green"
            )
        except Exception as e:
            console.print(f"[red]Error:[/red] Could not set default output style: {e}")
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(1)

    try:
        cfg = config.load_config()
        api_key = config.get_api_key(cfg)
        output_style = args.output or config.get_output_style(cfg)
    except ApiKeyNotFound:
        console.print(
            "[yellow]Gemini API key not found. Launching setup TUI...[/yellow]\n"
            "You can also set the key manually via the GEMINI_API_KEY environment variable "
            "or the config file."
        )
        try:
            api_key = tui.run_api_key_setup()
            if api_key:
                cfg = config.load_config() # Reload config after TUI updates it.
                output_style = args.output or config.get_output_style(cfg)
            else:
                raise ApiKeySetupCancelled("API Key setup cancelled.")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Setup cancelled:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error during API key setup:[/red] {e}")
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)

    try:
        response = gemini.generate_command(args.query, api_key)
        if not response:
            console.print("[red]Error:[/red] No response received from the AI model.")
            sys.exit(1)

        if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
            response_data = {"query": args.query, "command": response}
            action = tui.display_response_tui(response_data)

            if action == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(response)
                    console.print("[green]Command copied to clipboard![/green]")
                else:
                    console.print(
                        "[yellow]pyperclip not installed. Please install it to use the copy feature.[/yellow]"
                    )
                    console.print(f"[blue]Command:[/blue] {response}")

            elif action == "execute":
                execute_command(response, args.dry_run)
            elif action == "modify":
                # For simplicity, print the command and let the user manually modify it.
                console.print(f"[blue]Command:[/blue] {response} (Modify as needed and execute)")
            elif action == "refine":
                console.print("[yellow]Refine query feature not yet implemented.[/yellow]") # Placeholder
            else:
                pass # User cancelled or no action.

        else:  # Inline output
            console.print(f"[blue]Query:[/blue] {args.query}")
            console.print(f"[blue]Command:[/blue] {response}")
            if Confirm.ask("Execute command?"):
                execute_command(response, args.dry_run)

        # Save interaction history
        history.save_interaction(args.query, response)

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}")
        sys.exit(1)
    except OneQError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {e}")
        console.print_exception()  # Print the full traceback for debugging
        sys.exit(1)

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
        import oneq_cli.history as history # Import history module
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()