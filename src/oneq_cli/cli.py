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

console = Console(stderr=True)

def execute_command(command: str) -> None:
    """Executes a shell command."""
    try:
        # Use shlex.split to handle quoted arguments correctly
        args = shlex.split(command)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if stdout:
            console.print("Stdout:\n", style="bold green")
            console.print(stdout.decode())
        if stderr:
            console.print("Stderr:\n", style="bold red")
            console.print(stderr.decode())

        if process.returncode != 0:
            console.print(f"Command failed with return code: {process.returncode}", style="bold red")

    except FileNotFoundError:
        console.print(f"Command not found: {command}", style="bold red")
    except subprocess.CalledProcessError as e:
        console.print(f"Command execution failed: {e}", style="bold red")
    except Exception as e:
        console.print(f"An unexpected error occurred: {e}", style="bold red")


def main():
    parser = argparse.ArgumentParser(
        description="1Q - The right one-liner is just one query away."
    )
    parser.add_argument("query", nargs="?", help="The query to translate into a command.")
    parser.add_argument(
        "-k", "--api-key", dest="api_key", help="Manually specify the Gemini API key. Overrides config default."
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Specify the output style: auto (TUI if interactive, inline otherwise), tui (Textual UI), or inline (plain text). Overrides config default.",
    )
    parser.add_argument(
        "--show-config-path", action="store_true", help="Print the path to the configuration file and exit."
    )
    parser.add_argument(
        "--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation)."
    )
    parser.add_argument(
        "--set-default-output",
        dest="style",
        metavar="STYLE",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Set and save the default output style in the config file (auto, tui, inline).",
    )
    parser.add_argument("-v", "--version", action="version", version="1.0.0")

    args = parser.parse_args()

    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?"):
            config.clear_config_file()
        sys.exit(0)

    if args.style:
        try:
            config.set_default_output_style(args.style)
            console.print(f"Default output style set to: {args.style}", style="green")
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)

    api_key = args.api_key

    if not api_key:
        try:
            api_key = config.get_api_key()
        except ApiKeyNotFound:
            console.print("[yellow]Gemini API key not found. Launching setup...[/yellow]")
            try:
                api_key = tui.run_api_key_setup()  # type: ignore
                if api_key:
                    config.save_api_key(api_key)
                    console.print("[green]API key saved successfully![/green]")
                else:
                    raise ApiKeySetupCancelled("API key setup cancelled.")
            except ApiKeySetupCancelled as e:
                console.print(f"[red]Error:[/red] {e} Exiting.", style="red")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]An unexpected error occurred during API key setup: {e}[/red]", style="red")
                sys.exit(1)

    if not api_key:
        console.print("[red]Gemini API key is required. Please set it using --api-key or run the setup.[/red]", style="red")
        sys.exit(1)

    query = args.query
    if not query:
        query = Prompt.ask("Enter your query")

    output_style = args.output or config.get_default_output_style()

    try:
        response = gemini.generate_command(api_key, query)
        if not response:
            console.print("[red]Error: Could not generate a command.[/red]", style="red")
            sys.exit(1)

        command = response.get("command")
        explanation = response.get("explanation")

        if command:
            history.save_history(query, command)

        if output_style == "inline":
            console.print(f"[bold green]Command:[/bold green] {command}")
            if explanation:
                console.print(f"[bold green]Explanation:[/bold green] {explanation}")
        else: # auto or tui
            if output_style == "auto" and not sys.stdin.isatty():
                console.print(f"[bold green]Command:[/bold green] {command}")
                if explanation:
                    console.print(f"[bold green]Explanation:[/bold green] {explanation}")
            else:
                response_data = {"query": query, "command": command, "explanation": explanation}
                action = tui.display_response_tui(response_data) # type: ignore

                if action == "execute":
                    execute_command(command)
                elif action == "modify":
                    new_command = Prompt.ask("Enter the modified command", default=command)
                    execute_command(new_command)
                elif action == "refine":
                     new_query = Prompt.ask("Enter a refined query", default=query)
                     #Re-run the query
                     args.query = new_query
                     main() # Recursive call to re-process with refined query. Avoid excessive recursion depth.
                elif action == "copy":
                    if PYPERCLIP_AVAILABLE:
                        try:
                            pyperclip.copy(command)
                            console.print("[green]Command copied to clipboard![/green]")
                        except pyperclip.PyperclipException:
                            console.print("[red]Error: Could not copy to clipboard. Ensure you have xclip or xsel installed.[/red]", style="red")
                    else:
                        console.print("[red]Error: pyperclip is not installed. Please install it to use the copy feature.[/red]", style="red")
        sys.exit(0)

    except ApiKeyNotFound:
        console.print("[red]Gemini API key not found. Please configure it.[/red]", style="red")
        sys.exit(1)
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error: {e}[/red]", style="red")
        sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]", style="red")
        sys.exit(1)

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