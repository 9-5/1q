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

def _is_running_in_docker() -> bool:
    """Detect if the script is running inside a Docker container."""
    return Path("/.dockerenv").exists()

def _detect_wsl() -> bool:
    """Detect if the script is running inside Windows Subsystem for Linux (WSL)."""
    return "microsoft" in platform.uname().release.lower()

def execute_command(command: str, interactive: bool = False) -> Tuple[int, str, str]:
    """
    Executes a shell command.

    Args:
        command: The command string to execute.
        interactive: If True, runs the command in interactive mode.

    Returns:
        A tuple containing the return code, stdout, and stderr.
    """
    try:
        if interactive:
            # Interactive mode: pass the command directly to the shell
            process = subprocess.Popen(command, shell=True, executable=os.environ.get("SHELL"),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # Non-interactive mode: use shlex to split the command
            command_list = shlex.split(command)
            process = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()
        return_code = process.returncode
        stdout_str = stdout.decode("utf-8", errors="ignore")
        stderr_str = stderr.decode("utf-8", errors="ignore")

        return return_code, stdout_str, stderr_str
    except FileNotFoundError as e:
        return 127, "", f"Command not found: {e.filename}"
    except Exception as e:
        return 1, "", str(e)

def print_command_feedback(return_code: int, stdout: str, stderr: str) -> None:
    """Prints the output and errors from a command execution."""
    if stdout:
        console.print("Output:\n", style="bold green")
        console.print(stdout)
    if stderr:
        console.print("Errors:\n", style="bold red")
        console.print(stderr)
    if return_code != 0:
        console.print(f"Command failed with return code: {return_code}", style="bold red")
    else:
        console.print("Command executed successfully.", style="bold green")

def setup_api_key_interactive() -> Optional[str]:
    """Sets up the Gemini API key interactively using a TUI or command line prompts."""
    try:
        api_key = tui.run_api_key_setup()
        if api_key:
            config.save_api_key(api_key)
            console.print("API key saved successfully!", style="bold green")
            return api_key
        else:
            raise ApiKeySetupCancelled("API key setup cancelled.")
    except ImportError:
        console.print("[yellow]Textual TUI is not available. Falling back to command-line prompt.[/]")
        api_key = Prompt.ask("Please enter your Gemini API key")
        config.save_api_key(api_key)
        console.print("API key saved successfully!", style="bold green")
        return api_key
    except ApiKeySetupCancelled:
        console.print("API key setup cancelled.", style="yellow")
        return None

def get_gemini_response(prompt: str) -> Optional[Dict[str, Any]]:
    """Retrieves a command generation response from the Gemini API."""
    try:
        api_key = config.get_api_key()
        if not api_key:
            raise ApiKeyNotFound("Gemini API key not found. Please set it using --configure.")

        response = gemini.generate_command(prompt, api_key=api_key)
        return response
    except ApiKeyNotFound as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        if Confirm.ask("Do you want to set up the API key now?", default=True):
            setup_api_key_interactive()
        return None
    except GeminiApiError as e:
         console.print(f"[red]Gemini API Error:[/red] {e}", style="red")
         return None
    except Exception as e:
        console.print(f"[red]Unexpected Error:[/red] {e}", style="red")
        return None

def process_query(query: str) -> Optional[Dict[str, Any]]:
    """Processes the user query, retrieves the Gemini response, and handles errors."""
    try:
        response_data = get_gemini_response(query)
        return response_data

    except ApiKeyNotFound:
        if Confirm.ask("No API key found. Do you want to configure it now?", default=True):
            setup_api_key_interactive()
        return None
    except GeminiApiError as e:
        console.print(f"[red]Error:[/red] Gemini API failed: {e}", style="red")
        return None
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {e}", style="red")
        return None

def handle_output(response_data: Dict[str, Any], output_style: str) -> None:
    """Handles the output based on the configured output style."""
    if output_style == "tui":
        try:
            tui_result = tui.display_response_tui(response_data)
            if tui_result.action == "execute":
                execute_selected_command(response_data["command"])
            elif tui_result.action == "modify":
                # TODO: Implement command modification
                console.print("[yellow]Command modification is not yet implemented.[/]")
            elif tui_result.action == "refine":
                 # TODO: Implement query refinement
                 console.print("[yellow]Query refinement is not yet implemented.[/]")

        except ImportError:
            console.print("[yellow]Textual TUI is not available. Falling back to inline output.[/]")
            print_inline_output(response_data)
    elif output_style == "inline" or output_style == "auto":
        print_inline_output(response_data)

def print_inline_output(response_data: Dict[str, Any]) -> None:
    """Prints the command and explanation in the console."""
    console.print("Explanation:", style="bold blue")
    console.print(response_data["explanation"])
    console.print("\nCommand:", style="bold green")
    console.print(response_data["command"])

    if PYPERCLIP_AVAILABLE and Confirm.ask("Copy command to clipboard?", default=True):
        try:
            pyperclip.copy(response_data["command"])
            console.print("Command copied to clipboard!", style="green")
        except pyperclip.PyperclipException as e:
            console.print(f"[red]Error:[/red] Could not copy to clipboard: {e}", style="red")

    if Confirm.ask("Execute command?", default=False):
        execute_selected_command(response_data["command"])

def execute_selected_command(command: str) -> None:
    """Executes the given command and prints the feedback."""
    interactive = Confirm.ask("Run command in interactive mode (shell)?", default=False)
    return_code, stdout, stderr = execute_command(command, interactive=interactive)
    print_command_feedback(return_code, stdout, stderr)

def main():
    parser = argparse.ArgumentParser(description="1Q - The right one-liner is just one query away.",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("query", nargs="?", help="The natural language query for generating commands.")

    # Display and Configuration Actions
    config_group = parser.add_argument_group("Display and Configuration",
                                            "These actions configure 1q or display useful information. Requires arguments like --set-default-output STYLE, STYLE being a valid option (auto, tui, inline).\n"
                                            "Missing arguments or invalid options result in no change to the config default.")

    config_group.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    config_group.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")
    config_group.add_argument("--set-default-output", dest="set_default_output", choices=get_args(config.VALID_OUTPUT_STYLES), metavar="STYLE",
                            help="Set and save the default output style in the config file (auto, tui, inline).")
    config_group.add_argument("-v", "--version", action="version", version="1Q 1.0.0")

    args = parser.parse_args()

    if args.show_config_path:
        console.print(f"Configuration file path: {config.get_config_file_path()}")
        return

    if args.clear_config:
        if Confirm.ask("Are you sure you want to remove the configuration file?", default=False):
            config.clear_config_file()
        return

    if args.set_default_output:
        try:
            config.set_output_style(args.set_default_output)
            console.print(f"Default output style set to: {args.set_default_output}", style="green")
        except ConfigurationError as e:
            console.print(f"[red]Error:[/red] {e}", style="red")
        return

    if args.query:
        output_style = config.get_output_style()
        response_data = process_query(args.query)

        if response_data:
            handle_output(response_data, output_style)
    else:
        console.print("Hello, world! No query provided.")

if __name__ == "__main__":
    # Add src/ to path when running from source
    # This simplifies running the script directly from the source directory.
    # SCRIPT_DIR = Path(__file__).resolve().parent
    # sys.path.insert(0, str(SCRIPT_DIR.parent))
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