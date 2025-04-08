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

console = Console(stderr=True)

def main():
    parser = argparse.ArgumentParser(
        description="1Q - The right one-liner is just one query away.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="The query to resolve into a command.")
    parser.add_argument(
        "-o",
        "--output",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Output style (auto, tui, inline). Overrides config default.",
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
        dest="default_output_style",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument("-v", "--version", action="version", version="1.0.0")

    args = parser.parse_args()

    # Handle configuration-related actions first
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        else:
            console.print("Clear config cancelled.", style="yellow")
        sys.exit(0)

    if args.default_output_style:
        try:
            config.set_default_output_style(args.default_output_style)
            console.print(
                f"Default output style set to '{args.default_output_style}'.",
                style="green",
            )
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    # Load configuration and API key
    try:
        cfg = config.load_config()
        api_key = cfg.get(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY)
    except ApiKeyNotFound:
        console.print(
            "[yellow]Gemini API key not found. Launching setup...[/yellow]",
            style="yellow",
        )
        api_key = tui.run_api_key_setup()
        if api_key:
            try:
                config.save_api_key(api_key)
                console.print("[green]API key saved successfully![/green]", style="green")
            except config.ConfigurationError as e:
                console.print(f"[red]Error saving API key: {e}[/red]", style="red")
        else:
            console.print(
                "[red]API Key setup cancelled. Exiting.[/red]", style="red"
            )
            sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]", style="red")
        sys.exit(1)
    except ApiKeySetupCancelled:
        console.print("[red]API Key setup cancelled. Exiting.[/red]", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error during setup: {e}[/red]", style="red")
        sys.exit(1)

    # Determine output style
    output_style = args.output or cfg.get(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, fallback=config.DEFAULT_OUTPUT_STYLE)

    # Handle the query
    query = args.query
    if not query:
        console.print(
            "[yellow]No query provided. Please provide a query to 1q.[/yellow]",
            style="yellow",
        )
        sys.exit(1)

    try:
        response = gemini.generate_command(api_key, query)
        if not response:
            console.print("[red]No response received from the AI.[/red]", style="red")
            sys.exit(1)

        # Prepare response data for different output styles.
        response_data: Dict[str, Any] = {
            "query": query,
            "command": response,
        }

        if output_style == "tui":
            tui_result = tui.display_response_tui(response_data)

            if tui_result == "execute":
                command_to_execute = response_data.get("command")
                if command_to_execute:
                    try:
                        console.print(
                            "[bold blue]Executing command:[/bold blue] "
                            f"[italic]{command_to_execute}[/italic]"
                        )
                        # Execute the command using subprocess
                        process = subprocess.Popen(
                            command_to_execute,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        stdout, stderr = process.communicate()

                        # Decode and print the output
                        if stdout:
                            console.print("[bold green]Output:[/bold green]")
                            console.print(stdout.decode())
                        if stderr:
                            console.print("[bold red]Error:[/bold red]")
                            console.print(stderr.decode())
                    except FileNotFoundError:
                        console.print(
                            "[red]Error: Command not found. Make sure it's in your PATH.[/red]"
                        )
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Command failed with error: {e}[/red]")
                    except Exception as e:
                        console.print(f"[red]An unexpected error occurred: {e}[/red]")
                else:
                    console.print("[yellow]No command to execute.[/yellow]")

            elif tui_result == "copy":
                command_to_copy = response_data.get("command")
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command_to_copy)
                    console.print("[green]Command copied to clipboard![/green]")
                else:
                    console.print(
                        "[yellow]pyperclip not installed. Cannot copy to clipboard. "
                        "Please install it with 'pip install pyperclip'[/yellow]"
                    )

            elif tui_result == "modify":
                modified_command = Prompt.ask(
                    "[yellow]Modify command:[/yellow]", default=response_data["command"]
                )
                response_data["command"] = modified_command  # Update with modified command
                console.print(
                    "[bold blue]Modified command:[/bold blue] "
                    f"[italic]{modified_command}[/italic]"
                )
                # Optionally, save modified command back to history, or execute
                # For simplicity, this example just prints the modified command

            elif tui_result == "refine":
                refined_query = Prompt.ask(
                    "[yellow]Refine your query:[/yellow]", default=query
                )
                # Recursive call to process the refined query
                args.query = refined_query  # Update args with the refined query
                main()  # Call main again with the updated query
                return # Prevent further execution of the current call to main

        elif output_style == "inline":
            console.print(f"[bold blue]Query:[/bold blue] {query}")
            console.print(f"[bold green]Command:[/bold green] [italic]{response}[/italic]")
            if PYPERCLIP_AVAILABLE:
                pyperclip.copy(response)
                console.print("[green]Command copied to clipboard![/green]")
            else:
                console.print(
                    "[yellow]pyperclip not installed. Cannot copy to clipboard. "
                    "Please install it with 'pip install pyperclip'[/yellow]"
                )
        else:  # "auto" or any other unexpected value
            if console.is_terminal:
                # If running in a terminal, use TUI
                tui_result = tui.display_response_tui(response_data)
            else:
                # If not in a terminal (e.g., piped output), use inline
                console.print(f"[bold blue]Query:[/bold blue] {query}")
                console.print(f"[bold green]Command:[/bold green] [italic]{response}[/italic]")
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error: {e}[/red]", style="red")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]", style="red")


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