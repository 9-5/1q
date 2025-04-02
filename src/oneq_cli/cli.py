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
    """
    Main entry point for the 1Q CLI application.
    """
    # CLI argument parsing
    parser = argparse.ArgumentParser(
        description="1Q: Get the right one-liner with one query.",
        epilog="Example: 1q list files in Documents ending with .pdf",
    )

    # Add arguments
    parser.add_argument("query", nargs="*", help="Natural language query")
    parser.add_argument(
        "-s", "--style", type=str, choices=get_args(Literal["auto", "tui", "inline"]),
        help="Output style (auto, tui, inline)",
    )
    parser.add_argument(
        "--show-config-path", action="store_true",
        help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config", action="store_true",
        help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output", type=str, choices=get_args(Literal["auto", "tui", "inline"]),
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )
    parser.add_argument(
        "-v", "--version", action="store_true",
        help="show program's version number and exit"
    )

    args = parser.parse_args()

    if args.version:
        from oneq_cli import __version__
        print(f"1q version {__version__}")
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
            console.print(f"Default output style set to: {args.set_default_output}", style="green")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)


    # Load configuration
    try:
        cfg = config.load_config()
        api_key = cfg.get(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY)
    except ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found. Please set it up.[/yellow]")
        try:
            api_key = tui.ApiKeyApp.run()
            if api_key is None:
                raise ApiKeySetupCancelled("API key setup cancelled.")
            config.save_api_key(api_key)
            console.print("[green]API key saved successfully![/green]")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error loading configuration:[/red] {e}", style="red")
        sys.exit(1)


    # Determine output style
    output_style = args.style or config.get_output_style()

    # Process query
    query = " ".join(args.query)
    if not query:
        console.print("[yellow]Please provide a query.[/yellow]")
        sys.exit(1)

    try:
        response = gemini.generate_command(api_key, query)
        if response:
            if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
                response_data = {"query": query, "command": response}
                tui_result = tui.display_response_tui(response_data)

                if tui_result.action == "execute":
                    if tui_result.command_text:  # Execute only if there's a command
                        try:
                            # Sanitize the command to prevent injection attacks
                            sanitized_command = shlex.split(tui_result.command_text)
                            result = subprocess.run(sanitized_command, shell=False, capture_output=True, text=True)
                            console.print(f"Command Output:\n{result.stdout}")
                            if result.stderr:
                                console.print(f"[red]Command Error Output:\n{result.stderr}[/red]")
                        except FileNotFoundError:
                            console.print("[red]Error: Command not found. Please ensure it is in your PATH.[/red]")
                        except subprocess.CalledProcessError as e:
                            console.print(f"[red]Error: Command failed with return code {e.returncode}.[/red]")
                            console.print(f"[red]Error Output:\n{e.stderr}[/red]")
                        except Exception as e:
                            console.print(f"[red]An unexpected error occurred during command execution: {e}[/red]")
                elif tui_result.action == "modify":
                    # Handle modify action, perhaps by re-prompting the user with the current command
                    console.print("[yellow]Command modification requested. This feature is not yet implemented.[/yellow]")
                elif tui_result.action == "refine":
                     # Handle refine action by reprompting user.
                     console.print("[yellow]Query refinement requested. This feature is not yet implemented.[/yellow]")
                elif tui_result.action == "copy":
                    if PYPERCLIP_AVAILABLE and tui_result.command_text:
                        pyperclip.copy(tui_result.command_text)
                        console.print("[green]Command copied to clipboard![/green]")
                    else:
                        console.print("[red]pyperclip is not installed or no command to copy.[/red]")

                # Save history after a successful TUI interaction
                history.save_interaction(query, response)
            else:
                print(response)
                history.save_interaction(query, response) # Save history
        else:
            console.print("[red]No command generated.[/red]")

    except ApiKeyNotFound:
        console.print("[red]Gemini API key not found. Please set it up using --set-api-key.[/red]")
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error: {e}[/red]")
    except OneQError as e:
        console.print(f"[red]1Q Error: {e}[/red]")
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
        import oneq_cli.history as history # Import history module
        from oneq_cli.exceptions import ApiKeyNotFound, ConfigurationError, ApiKeySetupCancelled, GeminiApiError, OneQError
    except ImportError as e:
        print(f"Error: Could not import local modules from src/: {e}", file=sys.stderr)
        print("Ensure script is run from the project root or the project is installed.", file=sys.stderr)
        sys.exit(1)

    main()