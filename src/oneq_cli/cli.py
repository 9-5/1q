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
from . import history
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
    """
    Main entry point for the 1Q CLI application.
    """
    parser = argparse.ArgumentParser(
        description="1Q: Get the right one-liner command with natural language.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Natural language query for the command.")
    parser.add_argument(
        "-s",
        "--style",
        choices=["auto", "tui", "inline"],
        default="auto",
        help="Output style: auto (default), tui (Textual UI), inline (plain text).",
    )
    parser.add_argument(
        "-e",
        "--execute",
        action="store_true",
        help="Execute the generated command directly (use with caution!).",
    )
    parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy the generated command to the clipboard.",
    )
    parser.add_argument(
        "-ig",
        "--ignore-default",
        action="store_true",
        help="Ignore default configuration and use command-line arguments.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="1Q 1.0.0",  # Replace with actual version string
    )

    # Configuration and Info Actions
    config_group = parser.add_argument_group("Configuration and Info Actions")
    config_group.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the path to the configuration file and exit.",
    )
    config_group.add_argument(
        "--clear-config",
        action="store_true",
        help="Remove the configuration file (prompts for confirmation).",
    )
    config_group.add_argument(
        "--set-default-output",
        dest="default_output_style",
        choices=["auto", "tui", "inline"],
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )

    args = parser.parse_args()

    # Handle Config Info Actions
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        sys.exit(0)

    if args.default_output_style:
        try:
            config.set_output_style(args.default_output_style)
            console.print(f"Default output style set to: {args.default_output_style}", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)


    # Load configuration (unless --ignore-default is set)
    cfg = None
    if not args.ignore_default:
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print(
                "[yellow]Warning:[/yellow] Configuration file not found. Using defaults.",
                style="yellow",
            )
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)

    # Determine output style (command-line argument overrides config)
    output_style = args.style
    if args.style == "auto":
        if cfg and cfg.has_option("Settings", "output_style"):
            output_style = cfg.get("Settings", "output_style")
        else:
            output_style = config.DEFAULT_OUTPUT_STYLE
    
    # Check for API key
    try:
        api_key = config.get_api_key(cfg)
    except ApiKeyNotFound:
        console.print(
            "[yellow]Warning:[/yellow] Gemini API key not found. Launching setup...",
            style="yellow",
        )
        try:
            api_key = tui.ApiKeyApp().run()
            if api_key is None:
                raise ApiKeySetupCancelled("API Key setup cancelled.")
            config.save_api_key(api_key)
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] An unexpected error occurred during API key setup: {e}", style="red")
            sys.exit(1)

    query = " ".join(args.query)
    if not query:
        console.print("Please provide a query.", style="yellow")
        sys.exit(1)

    try:
        response_data = gemini.generate_command(query, api_key)
    except GeminiApiError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)

    if output_style == "tui":
        try:
            result = tui.display_response_tui(response_data)

            if result.action == "execute":
                # Execute the command
                if result.command:
                    try:
                        console.print(f"Executing: {result.command}", style="green")
                        subprocess.run(result.command, shell=True, check=True)
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error:[/red] Command failed: {e}", style="red")
                    except FileNotFoundError as e:
                        console.print(f"[red]Error:[/red] Command not found: {e}", style="red")
                    except Exception as e:
                        console.print(f"[red]Error:[/red] An unexpected error occurred during command execution: {e}", style="red")
                else:
                     console.print("[yellow]Warning:[/yellow] No command to execute.", style="yellow")

            elif result.action == "modify":
                # Allow user to modify the command (implementation depends on your TUI)
                if result.command:
                    console.print("[yellow]Allowing modification of command (feature not fully implemented yet).[/yellow]", style="yellow")
                    # You might want to open a text editor or provide an input field in the TUI here.
                else:
                    console.print("[yellow]Warning:[/yellow] No command to modify.", style="yellow")

            elif result.action == "refine":
                 console.print("[yellow]Allowing refinement of query (feature not fully implemented yet).[/yellow]", style="yellow")

            elif result.action == "copy":
                if result.command:
                    try:
                        if PYPERCLIP_AVAILABLE:
                            pyperclip.copy(result.command)
                            console.print("[green]Command copied to clipboard![/green]", style="green")
                        else:
                            console.print("[yellow]pyperclip is not installed. Please install it to use the copy feature.[/yellow]")
                    except Exception as e:
                         console.print(f"[red]Error:[/red] An unexpected error occurred during command copy: {e}", style="red")

            elif result.action == "view_history":
                 tui.display_history_tui()

            # No action implies cancelled.
            else:
                console.print("Action cancelled.", style="yellow")

            if result.query and result.command:
                history.save_history(result.query, result.command)

        except Exception as e:
            console.print(f"[red]Error:[/red] An unexpected error occurred in TUI mode: {e}", style="red")

    else:  # Inline mode
        if response_data and "command" in response_data:
            command = response_data["command"]
            console.print(f"Generated Command:\n{command}", style="green")

            if args.execute:
                try:
                    console.print(f"Executing: {command}", style="green")
                    subprocess.run(command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Error:[/red] Command failed: {e}", style="red")
                except FileNotFoundError as e:
                    console.print(f"[red]Error:[/red] Command not found: {e}", style="red")
                except Exception as e:
                    console.print(f"[red]Error:[/red] An unexpected error occurred during command execution: {e}", style="red")
            
            if args.copy:
                try:
                    if PYPERCLIP_AVAILABLE:
                        pyperclip.copy(command)
                        console.print("[green]Command copied to clipboard![/green]", style="green")
                    else:
                        console.print("[yellow]pyperclip is not installed. Please install it to use the copy feature.[/yellow]")
                except Exception as e:
                     console.print(f"[red]Error:[/red] An unexpected error occurred during command copy: {e}", style="red")

            history.save_history(query, command)

        else:
            console.print("[yellow]No command generated.[/yellow]", style="yellow")

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
        import oneq_cli.history as history_mod
        history = history_mod
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()