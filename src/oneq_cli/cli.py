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

def main():
    parser = argparse.ArgumentParser(
        description="1Q: The right one-liner is just one query away.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Natural language query for the command.")
    parser.add_argument(
        "-s",
        "--style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        default="auto",
        help="Output style (auto, tui, inline), overrides config default.",
    )
    parser.add_argument(
        "--show-config-path", action="store_true", help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output",
        dest="default_output_style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument("-v", "--version", action="store_true", help="show program's version number and exit")

    args = parser.parse_args()

    if args.version:
        from oneq_cli.config import APP_NAME
        from pyproject_toml import read_project
        project_data = read_project(Path(__file__).parent.parent.parent)
        version = project_data.get('project', {}).get('version', 'unknown')
        print(f"{APP_NAME} v{version}")
        sys.exit(0)

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        sys.exit(0)

    if args.default_output_style:
        try:
            config.set_default_output_style(args.default_output_style)
            console.print(f"Default output style set to: {args.default_output_style}", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    query = " ".join(args.query).strip()

    if not query:
        console.print("Please provide a query.", style="yellow")
        sys.exit(1)

    try:
        cfg = config.load_config()
        api_key = cfg.get(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY)
        output_style = args.style if args.style != "auto" else cfg.get(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, fallback=config.DEFAULT_OUTPUT_STYLE)
    except ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found.[/yellow]")
        try:
            api_key = tui.ApiKeyApp.run()
            if api_key is None:
                raise ApiKeySetupCancelled("API Key setup cancelled.")
            config.save_api_key(api_key)
            console.print("[green]Gemini API key saved successfully![/green]")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] Failed to save API key: {e}", style="red")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]An unexpected error occurred during API key setup: {e}[/red]", style="red")
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}\nUsing default settings.", style="red")
        api_key = None  # This will force an error if the API key isn't in the env.
        output_style = config.DEFAULT_OUTPUT_STYLE
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]", style="red")
        sys.exit(1)

    try:
        response = gemini.generate_command(api_key, query)
        command = response.get("command", "")
        explanation = response.get("explanation", "")

        if output_style == "tui":
            response_data = {"query": query, "command": command, "explanation": explanation}
            tui_result = tui.display_response_tui(response_data)

            if tui_result == "execute":
                if command:
                    try:
                        console.print(f"Executing: [cyan]{command}[/cyan]")
                        subprocess.run(command, shell=True, check=True)
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error executing command:[/red] {e}", style="red")
                    except FileNotFoundError as e:
                        console.print(f"[red]Command not found:[/red] {e}", style="red")
                    except Exception as e:
                        console.print(f"[red]An unexpected error occurred during command execution:[/red] {e}", style="red")
                else:
                    console.print("[yellow]No command to execute.[/yellow]")

            elif tui_result == "modify":
                console.print("[yellow]Command modification is not yet implemented. Copy the command and modify it manually.[/yellow]") # Implement modification later.
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard.[/green]")
                else:
                     console.print("[yellow]pyperclip not installed, cannot copy to clipboard. Install it with `pip install pyperclip`[/yellow]")

            elif tui_result == "refine":
                console.print("[yellow]Query refinement is not yet implemented.[/yellow]") # Implement query refinement later.

            elif tui_result == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard.[/green]")
                else:
                     console.print("[yellow]pyperclip not installed, cannot copy to clipboard. Install it with `pip install pyperclip`[/yellow]")
            elif tui_result == "history":
                console.print("[yellow]History browsing is not yet implemented.[/yellow]")

        else:  # Inline output style
            console.print(f"[bold]Command:[/bold] [cyan]{command}[/cyan]")
            console.print(f"[bold]Explanation:[/bold] {explanation}")
            if PYPERCLIP_AVAILABLE:
                pyperclip.copy(command)
                console.print("[green]Command copied to clipboard.[/green]")
            else:
                 console.print("[yellow]pyperclip not installed, cannot copy to clipboard. Install it with `pip install pyperclip`[/yellow]")

        history.save_history(query, command)

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]", style="red")
        sys.exit(1)


if __name__ == "__main__":
    # Add the src directory to PYTHONPATH
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
        import oneq_cli.history as history_mod
        history = history_mod
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()