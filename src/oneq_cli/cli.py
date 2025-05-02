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

def main():
    parser = argparse.ArgumentParser(
        description="1Q: The right one-liner is just one query away.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="Natural language query for command generation.")
    parser.add_argument(
        "-s", "--style", choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Force output style (auto, tui, inline). Overrides config."
    )
    parser.add_argument(
        "-v", "--version", action="version", version="1q 1.0.0",
        help="Show program's version number and exit"
    )

    config_group = parser.add_argument_group("Configuration and Info Actions")
    config_group.add_argument(
        "--show-config-path", action="store_true",
        help="Print the path to the configuration file and exit."
    )
    config_group.add_argument(
        "--clear-config", action="store_true",
        help="Remove the configuration file (prompts for confirmation)."
    )
    config_group.add_argument(
        "--set-default-output", dest="default_output_style", choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )

    args = parser.parse_args()

    # Handle config-related actions *before* potentially needing the API key
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file? This action cannot be undone."):
            config.clear_config_file()
        sys.exit(0)

    if args.default_output_style:
        try:
            config.set_config_value(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, args.default_output_style)
            console.print(f"Default output style set to '{args.default_output_style}'.", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    try:
        # Load configuration and API key
        cfg = config.load_config()
        api_key = config.get_gemini_api_key(cfg)
        genai = gemini.init_gemini_api(api_key)

    except ApiKeyNotFound:
        console.print("[yellow]Gemini API key not found.[/yellow]")
        if Confirm.ask("Do you want to set up the API key now?"):
            try:
                api_key = tui.run_api_key_setup()
                if api_key:
                     cfg = config.load_config() # Reload config to get new api key value
                     config.set_config_value(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY, api_key)
                     console.print("[green]API key saved successfully![/green]")
                     genai = gemini.init_gemini_api(api_key) # Initialize Gemini after setting up key.
                else:
                    raise ApiKeySetupCancelled("API Key setup was cancelled.")

            except ApiKeySetupCancelled:
                console.print("[red]API key setup cancelled.[/red]")
                sys.exit(1) # Exit if API key setup is cancelled.
            except config.ConfigurationError as e:
                console.print(f"[red]Error:[/red] {e}", style="red")
                sys.exit(1)

        else:
            console.print("[yellow]Please set up the Gemini API key to use 1Q.[/yellow]")
            sys.exit(1)

    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {e}", style="red")
        sys.exit(1)

    if not args.query:
        console.print("Please provide a query.  Example: 1q list files in Documents ending with .pdf")
        sys.exit(1)

    query = args.query

    # Determine output style: CLI arg > config > default
    output_style = args.style or cfg.get(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, fallback=config.DEFAULT_OUTPUT_STYLE)

    try:
        response = gemini.generate_command(genai, query)
        full_response_text = response.text if response and hasattr(response, 'text') else "No response from Gemini."

        # Extract code block using regex.
        match = re.search(r"```(.*?)```", full_response_text, re.DOTALL)
        command_text = match.group(1).strip() if match else full_response_text.strip()

        history.save_history(query, command_text)

        if output_style == "tui":
            response_data = {
                "query": query,
                "command": command_text,
                "full_response": full_response_text,
            }
            tui_result = tui.display_response_tui(response_data)

            if tui_result == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command_text)
                    console.print("[green]Command copied to clipboard![/green]")
                else:
                    console.print("[red]pyperclip not installed. Please install it to copy to clipboard.[/red]")
            elif tui_result == "execute":
                try:
                    console.print(f"Executing command: [cyan]{command_text}[/cyan]")
                    process = subprocess.Popen(shlex.split(command_text), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    if stdout:
                        console.print("[bold]Output:[/bold]\n" + stdout.decode())
                    if stderr:
                        console.print("[bold red]Error:[/bold red]\n" + stderr.decode())
                    if not stdout and not stderr:
                        console.print("[italic]No output[/italic]")

                except FileNotFoundError as e:
                    console.print(f"[red]Error: Command not found: {e}[/red]")
                except Exception as e:
                    console.print(f"[red]Error executing command: {e}[/red]")
            elif tui_result == "modify":
                console.print("[yellow]Modify command action selected (feature not implemented yet).[/yellow]")
            elif tui_result == "refine":
                 console.print("[yellow]Refine query action selected (feature not implemented yet).[/yellow]")

        elif output_style == "inline" or output_style == "auto":
            # Inline output (or fallback from auto)
            console.print(f"[bold]Query:[/bold] {query}\n")
            console.print(f"[bold]Command:[/bold] [cyan]{command_text}[/cyan]\n")
            console.print(f"[bold]Full Response:[/bold]\n{full_response_text}")
        else:
            console.print(f"[red]Invalid output style: {output_style}[/red]")

    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {e}", style="red")

if __name__ == "__main__":
    # Add the project's src/ directory to the Python path
    # This allows running the script directly without installing the package
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