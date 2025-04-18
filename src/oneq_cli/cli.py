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

def main() -> None:
    parser = argparse.ArgumentParser(
        description="1Q: Get the right one-liner with one query.",
        epilog="Example: 1q list files in Documents ending with .pdf",
    )

    # Add arguments
    parser.add_argument("query", nargs="*", help="The query to generate a command.")
    parser.add_argument(
        "-s",
        "--style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        default="auto",
        help="Output style (auto, tui, inline). Overrides default.",
    )
    parser.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the path to the configuration file and exit.",
    )
    parser.add_argument(
        "--clear-config",
        action="store_true",
        help="Remove the configuration file (prompts for confirmation).",
    )
    parser.add_argument(
        "--set-default-output",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="show program's version number and exit"
    )

    args = parser.parse_args()

    if args.version:
        from oneq_cli.version import __version__
        print(__version__)
        sys.exit(0)


    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("[bold red]Are you sure you want to clear the configuration file?[/]", default=False):
            config.clear_config_file()
        sys.exit(0)

    if args.set_default_output:
        try:
            config_manager = config.ConfigManager()
            config_manager.set_output_style(args.set_default_output)
            config_manager.save_config()
            console.print(f"Default output style set to: [bold]{args.set_default_output}[/]")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(0)

    query = " ".join(args.query)

    if not query:
        console.print("Please provide a query.", style="bold red")
        sys.exit(1)

    try:
        api_key = config.get_gemini_api_key()
    except ApiKeyNotFound:
        console.print(
            "[bold yellow]Gemini API key not found. Please set it up using the TUI.[/]"
        )
        try:
            api_key = tui.run_api_key_setup()
            if api_key is None:
                raise ApiKeySetupCancelled("API key setup cancelled.")
        except ApiKeySetupCancelled as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error during API key setup:[/red] {e}")
            sys.exit(1)

    try:
        response = gemini.generate_command(api_key, query)
        command = response["command"]
        if command:
            save_history(query, command) # Save to history
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)

    output_style = args.style
    if output_style == "auto":
        config_manager = config.ConfigManager()
        output_style = config_manager.get_output_style()


    if output_style == "tui":
        response_data = {"query": query, "command": command}
        chosen_action = tui.display_response_tui(response_data)

        if chosen_action == "execute":
            if command:
                try:
                    # Execute the command
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    if process.returncode == 0:
                        console.print(f"[green]Command executed successfully.[/]\n[bold]Output:[/]\n{stdout.decode()}")
                    else:
                        console.print(f"[red]Command failed with error:[/]\n{stderr.decode()}")

                except FileNotFoundError:
                    console.print("[red]Error: Command not found. Make sure it's installed and in your PATH.[/]")
                except Exception as e:
                    console.print(f"[red]Error executing command:[/]\n{e}")
            else:
                console.print("[yellow]No command to execute.[/]")

        elif chosen_action == "modify":
            # For now, just print the command - future commits will handle modification.
            console.print(f"[bold]Command to modify:[/]\n{command}")

        elif chosen_action == "refine":
            # For now, just print the query - future commits will handle refinement.
            console.print(f"[bold]Original query:[/]\n{query}")

        elif chosen_action == "copy":
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard![/]")
                except pyperclip.PyperclipException:
                    console.print("[red]Error: Could not copy to clipboard.  Ensure you have 'xclip' or 'xsel' installed.[/]")
            else:
                console.print("[yellow]pyperclip is not installed. Please install it to copy to clipboard.[/]")


    else:  # inline
        print(command)



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