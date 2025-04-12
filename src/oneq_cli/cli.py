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
    """Executes a shell command and prints the output."""
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
        console.print(f"[bold green]Command Output:[/]")
        console.print(result.stdout)
        if result.stderr:
            console.print(f"[bold red]Command Error:[/]")
            console.print(result.stderr)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Command Failed:[/]")
        console.print(e.stderr)
    except FileNotFoundError:
        console.print(f"[bold red]Command Not Found:[/]")
    except Exception as e:
        console.print(f"[bold red]Error executing command:[/]")
        console.print(str(e))

def main() -> None:
    parser = argparse.ArgumentParser(
        description="1Q: Get the right one-liner command with a query.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="Natural language query for the desired command.")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute the generated command directly.")
    parser.add_argument(
        "-o",
        "--output",
        choices=["auto", "tui", "inline"],
        default="auto",
        help="Specify the output style:\n"
             "  - auto: Use TUI if possible, otherwise inline.\n"
             "  - tui:  Force Textual User Interface.\n"
             "  - inline: Force inline output (plain text).",
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
    parser.add_argument("-v", "--version", action="version", version="1Q 1.0.0")

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
            config.set_default_output_style(args.set_default_output)
            console.print(f"Default output style set to: {args.set_default_output}", style="green")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    try:
        api_key = config.get_gemini_api_key()
    except ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found.[/yellow]")
        try:
            api_key = tui.ask_for_api_key()
            if api_key:
                config.save_gemini_api_key(api_key)
                console.print("[green]API key saved successfully![/green]")
            else:
                console.print("[red]API key setup cancelled. Exiting...[/red]")
                sys.exit(1)
        except ApiKeySetupCancelled:
            console.print("[red]API key setup cancelled. Exiting...[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]An unexpected error occurred: {e}[/red]")
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)

    # Initialize Gemini API
    try:
        gemini.init_gemini(api_key)
    except Exception as e:
        console.print(f"[red]Failed to initialize Gemini API: {e}[/red]")
        sys.exit(1)

    query = args.query.strip()
    output_style = args.output

    try:
        response = gemini.generate_command(query)
        command = response.get("command", "").strip()
        explanation = response.get("explanation", "").strip()

        if not command:
            console.print("[red]No command was generated.[/red]")
            sys.exit(1)

        if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
            response_data = {"query": query, "command": command, "explanation": explanation}
            tui_result = tui.display_response_tui(response_data)

            if tui_result == "execute":
                execute_command(command)
            elif tui_result == "modify":
                # TODO: Implement command modification (perhaps with another TUI)
                console.print("[yellow]Command modification not yet implemented.[/yellow]")
            elif tui_result == "refine":
                 # TODO: Implement query refinement
                console.print("[yellow]Query refinement not yet implemented.[/yellow]")

        else:  # Inline output
            console.print(f"[bold green]Query:[/ bold green] {query}")
            console.print(f"[bold blue]Command:[/ bold blue] {command}")
            console.print(f"[bold]Explanation:[/ bold]\n{explanation}")
            if args.execute:
                if Confirm.ask("Execute this command?"):
                    execute_command(command)
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)
    finally:
        # Save interaction to history.  Do this even on error, as query may be useful.
        if 'query' in locals() and 'command' in locals(): # Ensure these are defined.
            history.save_history(query, command)

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