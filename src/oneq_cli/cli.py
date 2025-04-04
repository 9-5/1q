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
    """Main entry point for the 1q CLI."""
    # Monkey-patch Rich to output emoji even on Windows cmd.exe
    if os.name == "nt" and sys.stdout.isatty():
        import rich.console
        rich.console.detect_modern_terminal = lambda: False

    parser = argparse.ArgumentParser(
        description="1Q: The right one-liner is just one query away.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Natural language query for the command.")
    parser.add_argument(
        "-s", "--style", choices=get_args(config.VALID_OUTPUT_STYLES),
        help="Output style (auto, tui, inline). Overrides config.",
        default=None
    )
    parser.add_argument(
        "-c", "--copy", action="store_true",
        help="Copy the generated command to the clipboard."
    )
    parser.add_argument(
        "-x", "--execute", action="store_true",
        help="Execute the generated command directly (after confirmation)."
    )
    parser.add_argument(
        "-ig", "--ignore-default", action="store_true",
        help="Ignore the default output style from the config."
    )
    parser.add_argument(
        "-v", "--version", action="version", version="1Q 1.0.0"
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
        "--set-default-output", choices=get_args(config.VALID_OUTPUT_STYLES),
        metavar="STYLE",
        help="Set and save the default output style in the config file (auto, tui, inline)."
    )


    args = parser.parse_args()

    # Handle configuration actions first (show path, clear config, set default)
    if args.show_config_path:
        print(config.get_config_file_path())
        sys.exit(0)

    if args.clear_config:
        if Confirm.ask("[yellow]Are you sure you want to remove the configuration file?[/]") :
            config.clear_config_file()
        else:
            console.print("Clear config cancelled.")
        sys.exit(0)

    if args.set_default_output:
        try:
            config.set_config_value(config.SETTINGS_SECTION, config.OUTPUT_STYLE_CONFIG_KEY, args.set_default_output)
            console.print(f"Default output style set to '{args.set_default_output}' in config.", style="green")
        except config.ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(0)


    query = " ".join(args.query)

    if not query:
        console.print("Please provide a query.", style="yellow")
        sys.exit(1)

    try:
        # Load configuration and API key
        cfg = config.load_config()
        api_key = config.get_api_key(cfg)
        output_style = args.style or (None if args.ignore_default else config.get_output_style(cfg)) or config.DEFAULT_OUTPUT_STYLE

        # Initialize Gemini API
        gemini.init_gemini(api_key)

        # Get the platform context (OS, shell)
        platform_context = gemini._get_platform_context()

        # Generate the command
        response_data = gemini.generate_command(query, platform_context)

        if not response_data or not response_data.get("command"):
            console.print("[red]Error:[/red] No command generated.", style="red")
            sys.exit(1)

        # Handle output based on style (auto, tui, inline)
        if output_style == "tui" or (output_style == "auto" and sys.stdout.isatty()):
            import oneq_cli.tui as tui_mod
            tui = tui_mod
            result = tui.display_response_tui(response_data)

            if result is None:
                sys.exit(0)  # User closed the TUI without action

            if result.action == "execute":
                command_to_execute = result.command
                if command_to_execute:
                    try:
                        print(f"Executing: {command_to_execute}")
                        subprocess.run(command_to_execute, shell=True, check=True)
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Error:[/red] Command failed: {e}", style="red")
                else:
                    console.print("[yellow]Warning:[/yellow] No command to execute.", style="yellow")
            elif result.action == "copy":
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(result.command)
                    console.print("[green]Command copied to clipboard![/]", style="green")
                else:
                    console.print("[red]Error:[/red] pyperclip not available. Please install it to use copy functionality.", style="red")
                    print(result.command) # Fallback: print the command
            elif result.action == "modify":
                console.print("[yellow]Command modification is not yet implemented. Please stay tuned![/]", style="yellow")
                print(response_data.get("command"))
            elif result.action == "refine":
                 console.print("[yellow]Query refinement is not yet implemented. Please stay tuned![/]", style="yellow")

        else:  # Inline output
            command = response_data.get("command")
            print(command)
            if args.copy:
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(command)
                    console.print("[green]Command copied to clipboard![/]", style="green")
                else:
                    console.print("[red]Error:[/red] pyperclip not available. Please install it to use copy functionality.", style="red")

            if args.execute:
                try:
                    print(f"Executing: {command}")
                    subprocess.run(command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Error:[/red] Command failed: {e}", style="red")

        # Save the interaction to history
        import oneq_cli.history as history_mod
        history_mod.save_history(query, response_data.get("command", "")) # Save command even if empty string

    except ApiKeyNotFound:
        console.print("[red]Error:[/red] Gemini API key not found.", style="red")
        console.print("Please set the GEMINI_API_KEY environment variable or configure it using the TUI.")
        if Confirm.ask("Do you want to set up the API key using the TUI?"):
            import oneq_cli.tui as tui_mod
            tui = tui_mod
            try:
                api_key = tui.run_api_key_setup()
                if api_key:
                    console.print("[green]API key setup successful![/]", style="green")
                    # Store the API key in the configuration file
                    try:
                        config.set_config_value(config.CREDENTIALS_SECTION, config.API_KEY_CONFIG_KEY, api_key)
                        console.print("[green]API key saved to configuration file.[/]", style="green")
                    except config.ConfigurationError as e:
                        console.print(f"[red]Error:[/red] Failed to save API key to config: {e}", style="red")

                else:
                    console.print("[yellow]API key setup cancelled.[/]", style="yellow")
            except tui.ApiKeySetupCancelled:
                console.print("[yellow]API key setup cancelled.[/]", style="yellow")

    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}", style="red")
    except GeminiApiError as e:
        console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
    except OneQError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred:[/red] {e}", style="red")
        console.print_exception() # Print the traceback


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