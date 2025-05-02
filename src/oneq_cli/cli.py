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

console = Console(stderr=True, highlight=False)
stdout_console = Console(highlight=False)

ConversationHistory = List[Dict[str, Any]] # Structure expected by gemini.generate_command

def create_parser() -> argparse.ArgumentParser:
    """Creates and configures the argument parser for the CLI."""
    try:
        import importlib.metadata
        version_string = importlib.metadata.version("oneq")
    except importlib.metadata.PackageNotFoundError:
        version_string = "0.0.0-dev" # Fallback if not installed

    parser = argparse.ArgumentParser(
        prog="1q",
        description="1Q: Your instant command-line and code snippet generator.",
        epilog="Example: 1q list files in Documents ending with .pdf"
    )
    parser.add_argument(
        "query",
        nargs='*', # Allow zero or more query words
        help="Your natural language query. If omitted, runs setup (if needed) or shows help."
    )
    parser.add_argument(
        "-o", "--output",
        choices=get_args(config.VALID_OUTPUT_STYLES),
        type=str.lower,
        default=None, # Default is read from config
        help="Specify output style for this run: 'auto', 'tui', 'inline'. Overrides config default."
    )
    action_group = parser.add_argument_group('Configuration and Info Actions')
    action_group.add_argument(
        "--show-config-path",
        action="store_true",
        help="Print the path to the configuration file and exit."
    )
    action_group.add_argument(
        "--clear-config",
        action="store_true",
        help="Remove the configuration file (prompts for confirmation)."
    )
    action_group.add_argument(
         "--set-default-output",
         choices=get_args(config.VALID_OUTPUT_STYLES),
         type=str.lower,
         metavar='STYLE',
         help=f"Set and save the default output style in the config file ({', '.join(get_args(config.VALID_OUTPUT_STYLES))})."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"1Q {version_string}"
    )
    return parser

def parse_gemini_response(response_text: str) -> Dict[str, Any]:
    """
    Parses the raw text response from Gemini into structured components.
    Filters out markdown code blocks from the command section if present.

    Args:
        response_text: The raw string response from the Gemini API.

    Returns:
        A dictionary containing 'command', 'explanation', 'install', and 'raw'.
        Keys will have None value if the corresponding section wasn't found.
    """
    parsed: Dict[str, Any] = {
        'command': None,
        'explanation': None,
        'install': None,
        'raw': response_text
    }
    command_marker = "COMMAND:"
    explanation_marker = "EXPLANATION:"
    install_marker = "INSTALL:"

    upper_text = response_text.upper()
    cmd_idx = upper_text.find(command_marker)
    exp_idx = upper_text.find(explanation_marker)
    inst_idx = upper_text.find(install_marker)

    markers_present = cmd_idx != -1 or exp_idx != -1 or inst_idx != -1

    if markers_present:
        indices = sorted([i for i in [cmd_idx, exp_idx, inst_idx] if i != -1])
        marker_map = {
            cmd_idx: ('command', command_marker),
            exp_idx: ('explanation', explanation_marker),
            inst_idx: ('install', install_marker),
        }

        content_map = {}
        for i, start_idx in enumerate(indices):
            key, marker = marker_map[start_idx]
            end_idx = indices[i+1] if i + 1 < len(indices) else len(response_text)
            content = response_text[start_idx + len(marker):end_idx].strip()
            content_map[key] = content if content else None

        parsed.update(content_map)

        # Ensure keys for markers not found are explicitly None
        for key in ['command', 'explanation', 'install']:
            if key not in content_map:
                parsed[key] = None
    else:
        # No Markers Found: Assume the entire stripped response is the command
        parsed['command'] = response_text.strip() if response_text.strip() else None
        parsed['explanation'] = None
        parsed['install'] = None

    # Filter Markdown Code Block from Command Section
    if parsed['command']:
        code_block_pattern = r'^```[^\n]*\n?(.*?)\n?```$'
        match = re.search(code_block_pattern, parsed['command'], re.DOTALL)
        if match:
            filtered_command = match.group(1).strip()
            parsed['command'] = filtered_command if filtered_command else None

    # Final cleanup: ensure empty strings are treated as None
    for key in ['command', 'explanation', 'install']:
        if isinstance(parsed[key], str) and not parsed[key]:
            parsed[key] = None

    return parsed


def run_setup_flow() -> Optional[str]:
    """
    Runs the interactive initial setup for API key and default output style.

    Returns:
        The API key if setup was successful, None otherwise (or if cancelled).
    """
    console.print("[bold yellow]Gemini API Key not found or configured.[/]")
    console.print("Launching setup...")
    try:
        api_key = tui.prompt_for_api_key()
        if api_key:
            config.save_api_key(api_key)
            default_style_choice = Prompt.ask(
                "Set default output style?",
                choices=list(get_args(config.VALID_OUTPUT_STYLES)),
                default=config.DEFAULT_OUTPUT_STYLE,
                console=console
            )
            config.save_output_style(default_style_choice) # type: ignore
            console.print("\n[bold green]API Key saved successfully.[/]")
            return api_key
        else:
            raise ApiKeySetupCancelled("API key setup was cancelled by the user.")
    except ApiKeySetupCancelled:
         console.print("[yellow]Setup cancelled.[/]")
         return None
    except (ConfigurationError, Exception) as e:
        console.print(f"[bold red]Error during setup:[/]\n {e}")
        return None

def execute_command(command: str) -> None:
    """
    Executes the given command string in the system's shell.

    Args:
        command: The command string to execute.
    """
    if not command:
        console.print("[yellow]Cannot execute an empty command.[/]")
        return
    console.print(f"\n[bold cyan]Executing:[/]\n$ {command}")
    try:
        # Using shell=True for simplicity but acknowledge security implications.
        result = subprocess.run(command, shell=True, check=False, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.stdout:
            console.print("[bold green]--- Output ---[/]")
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
            console.print("[bold green]--- End Output ---[/]")

        if result.stderr:
             console.print("[bold red]--- Error Output ---[/]")
             console.print(result.stderr.strip(), style="red")
             console.print("[bold red]--- End Error Output ---[/]")

        if result.returncode != 0:
            console.print(f"[yellow]Command exited with code {result.returncode}[/]")

    except FileNotFoundError:
         command_name = command.split()[0] if command else "command"
         console.print(f"[bold red]Error: Command not found.[/] Is '{command_name}' in your system's PATH?")
    except Exception as e:
        console.print(f"[bold red]Failed to execute command:[/]\n {e}")

def modify_command_interactive(command: str) -> Optional[str]:
    """
    Allows the user to modify the generated command interactively using Rich Prompt.

    Args:
        command: The initial command string to be modified.

    Returns:
        The modified command string, or None if modification was cancelled or cleared.
    """
    if not command:
        console.print("[yellow]Cannot modify an empty command.[/]")
        return None

    console.print("\n[bold yellow]--- Modify Command ---[/]")
    console.print("Edit the command below. Press Enter to confirm, Ctrl+C/Ctrl+D to cancel.")
    try:
        modified_command = Prompt.ask(
            "Edit Command", default=command, console=console
        )
        return modified_command.strip() if modified_command.strip() else None
    except (EOFError, KeyboardInterrupt):
        console.print("\nModification cancelled.")
        return None

def create_action_prompt(
    actions: List[Tuple[str, str, str]], # (Letter, Full Name, Description)
    default_action: str = 'q'
) -> Tuple[Text, List[str]]:
    """Creates the formatted prompt Text and the list of valid letter choices."""
    prompt_text = Text()
    choices = []
    for i, (letter, _, description) in enumerate(actions):
        choices.append(letter.lower())
        prompt_text.append(f"[{letter.upper()}]", style="bold underline")
        prompt_text.append(description, style="default")
        if i < len(actions) - 1:
            prompt_text.append(", ", style="default")
    prompt_text.append("? ", style="default")
    return prompt_text, choices

def main() -> None:
    """Main function for the 1Q CLI application."""
    parser = create_parser()
    args = parser.parse_args()

    # --- Handle Action Flags ---
    if args.set_default_output:
        try:
            config.save_output_style(args.set_default_output)
        except ConfigurationError as e:
            console.print(f"[bold red]Error saving configuration:[/]\n {e}")
            sys.exit(1)
        except Exception as e:
             console.print(f"[bold red]An unexpected error occurred:[/]\n {e}")
             sys.exit(1)
        sys.exit(0)

    if args.show_config_path:
        try:
            print(config.get_config_file_path())
        except Exception as e:
             console.print(f"[bold red]Error getting config path:[/]\n {e}")
             sys.exit(1)
        sys.exit(0)

    if args.clear_config:
        config_path_str = str(config.get_config_file_path())
        env_var_set = os.environ.get(config.API_KEY_ENV_VAR) is not None

        if not os.path.exists(config_path_str) and not env_var_set:
             console.print("No configuration file found and GEMINI_API_KEY environment variable not set. Nothing to clear.", style="yellow")
             sys.exit(0)

        prompt_msg = f"Are you sure you want to remove the configuration file '{config_path_str}'?"
        if env_var_set:
             prompt_msg += f"\nNote: The {config.API_KEY_ENV_VAR} environment variable is still set and will be used if present."

        if Confirm.ask(prompt_msg, default=False, console=console):
           try:
               config.clear_config_file()
           except Exception as e:
               console.print(f"[bold red]Error clearing configuration:[/]\n {e}")
               sys.exit(1)
        else:
           console.print("Operation cancelled.")
        sys.exit(0)

    # --- API Key Loading/Setup ---
    api_key: Optional[str] = None
    try:
        api_key = config.load_api_key()
    except ApiKeyNotFound:
        if not args.query:
             api_key = run_setup_flow()
             if not api_key:
                 sys.exit(1) # Setup failed or cancelled
             else:
                 console.print("\nSetup complete. Run `1q your query` to start, or `1q --help` for options.")
                 sys.exit(0)
        else:
             console.print("[bold red]Error:[/bold red] Gemini API Key not found.")
             console.print("Please set the GEMINI_API_KEY environment variable or run `1q` without arguments to configure.")
             sys.exit(1)
    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/]\n {e}")
        api_key_env = os.environ.get(config.API_KEY_ENV_VAR)
        if not api_key_env:
             console.print("API key also not found in environment variable. Exiting.")
             sys.exit(1)
        else:
             console.print(f"[yellow]Warning:[/yellow] Using API key from environment variable ({config.API_KEY_ENV_VAR}) despite config error.")
             api_key = api_key_env
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during configuration loading:[/]\n {e}")
        sys.exit(1)

    # --- Handle No Query Case (API key must exist here) ---
    if not args.query:
        parser.print_help(file=sys.stderr)
        sys.exit(0)

    # --- Determine Effective Output Style ---
    effective_output_style: Literal["auto", "tui", "inline"]
    if args.output:
        effective_output_style = args.output
    else:
        effective_output_style = config.load_output_style()

    # --- Conversation Loop ---
    conversation_history: ConversationHistory = []
    current_query: str = " ".join(args.query)
    last_command: Optional[str] = None

    base_inline_actions = [
        ('X', 'execute', 'ecute'),
        ('M', 'modify', 'odify'),
        ('R', 'refine', 'efine'),
    ]
    quit_action = ('Q', 'quit', 'uit')
    copy_action = ('C', 'copy', 'opy')

    while True:
        if not api_key:
             console.print("[bold red]Internal Error: API key became unavailable.[/]")
             sys.exit(1)

        try:
            with console.status("[bold cyan]Querying Gemini...", spinner="dots"):
                full_response_text = gemini.generate_command(
                    api_key=api_key,
                    user_query=current_query,
                    history=conversation_history
                )

            parsed_output = parse_gemini_response(full_response_text)
            last_command = parsed_output.get('command')

            conversation_history.append({'role': 'user', 'parts': [{'text': current_query}]})
            conversation_history.append({'role': 'model', 'parts': [{'text': full_response_text}]})

            # --- Decide Output Method ---
            output_mode: Literal["tui", "inline"]

            if effective_output_style == 'tui':
                output_mode = 'tui'
            elif effective_output_style == 'inline':
                output_mode = 'inline'
            else: # 'auto' logic
                has_details = parsed_output.get('explanation') or parsed_output.get('install')
                raw_upper_text = full_response_text.upper()
                raw_has_markers = "COMMAND:" in raw_upper_text or \
                                  "EXPLANATION:" in raw_upper_text or \
                                  "INSTALL:" in raw_upper_text

                # Use TUI if details exist OR raw response had markers (prioritizing structure)
                if has_details or (raw_has_markers and last_command):
                    output_mode = 'tui'
                elif last_command:
                    output_mode = 'inline'
                else:
                    console.print("[bold red]Error:[/bold red] Received an empty or unparseable response from Gemini.")
                    console.print("[dim]Raw Response:[/]", style="dim")
                    console.print(parsed_output.get('raw', 'N/A'), style="dim")
                    sys.exit(1)

            # --- Perform Output and Get User Action ---
            next_action: Optional[str] = None

            if output_mode == 'tui':
                if not last_command and not parsed_output.get('explanation') and not parsed_output.get('install'):
                     console.print("[bold red]Error:[/bold red] Cannot display empty response in TUI.")
                     console.print("[dim]Raw Response:[/]", style="dim")
                     console.print(parsed_output.get('raw', 'N/A'), style="dim")
                     sys.exit(1)

                tui_result: Optional[Literal["execute", "modify", "copy", "refine"]]
                tui_result = tui.display_response_tui(parsed_output)
                next_action = tui_result # None if user quit TUI

            elif output_mode == 'inline':
                if last_command:
                    # Print command ONLY to standard output
                    stdout_console.print(last_command, end="")
                    sys.stdout.flush()

                    # Print details to stderr
                    explanation = parsed_output.get('explanation')
                    install_steps = parsed_output.get('install')
                    if explanation or install_steps:
                         console.print("\n" + "-"*20)
                         if install_steps:
                              console.print(f"[cyan bold]Install:[/]\n{install_steps}")
                         if explanation:
                             console.print(f"[cyan bold]Explanation:[/]\n{explanation}")
                         console.print("-" * 20)
                    else:
                         # Add newline on stderr to separate stdout command from stderr prompt
                         console.print()

                    # Prompt for action on stderr
                    current_inline_actions = list(base_inline_actions)
                    if PYPERCLIP_AVAILABLE:
                        current_inline_actions.append(copy_action)
                    current_inline_actions.append(quit_action)

                    prompt_text, letter_choices = create_action_prompt(current_inline_actions)
                    action_map = {letter.lower(): full_name for letter, full_name, _ in current_inline_actions}

                    user_input_letter = Prompt.ask(
                        prompt_text,
                        choices=letter_choices,
                        default="q",
                        console=console,
                        show_choices=False
                    ).lower()

                    selected_action_name = action_map.get(user_input_letter)

                    # Handle inline copy action
                    if selected_action_name == 'copy':
                         if PYPERCLIP_AVAILABLE and last_command:
                             try:
                                 pyperclip.copy(last_command)
                                 console.print("[green]Command copied to clipboard.[/]")

                                 # Ask again what to do after copying (excluding copy)
                                 post_copy_actions = list(base_inline_actions)
                                 post_copy_actions.append(quit_action)
                                 post_copy_prompt, post_copy_choices = create_action_prompt(post_copy_actions)
                                 post_copy_map = {letter.lower(): full_name for letter, full_name, _ in post_copy_actions}

                                 action_after_copy_letter = Prompt.ask(
                                     post_copy_prompt,
                                     choices=post_copy_choices,
                                     default="q", console=console, show_choices=False
                                 ).lower()
                                 next_action = post_copy_map.get(action_after_copy_letter)

                             except Exception as e:
                                  console.print(f"[red]Error copying to clipboard: {e}[/]")
                                  # Ask again, excluding copy
                                  post_error_actions = list(base_inline_actions)
                                  post_error_actions.append(quit_action)
                                  post_error_prompt, post_error_choices = create_action_prompt(post_error_actions)
                                  post_error_map = {letter.lower(): full_name for letter, full_name, _ in post_error_actions}
                                  action_after_error_letter = Prompt.ask(
                                      post_error_prompt,
                                      choices=post_error_choices,
                                      default="q", console=console, show_choices=False
                                  ).lower()
                                  next_action = post_error_map.get(action_after_error_letter)
                         else:
                              console.print("[yellow]Copy action unavailable.[/]")
                              # Ask again, excluding copy
                              post_error_actions = list(base_inline_actions)
                              post_error_actions.append(quit_action)
                              post_error_prompt, post_error_choices = create_action_prompt(post_error_actions)
                              post_error_map = {letter.lower(): full_name for letter, full_name, _ in post_error_actions}
                              action_after_error_letter = Prompt.ask(
                                  post_error_prompt,
                                  choices=post_error_choices,
                                  default="q", console=console, show_choices=False
                              ).lower()
                              next_action = post_error_map.get(action_after_error_letter)
                    else:
                         # For execute, modify, refine, quit - set next_action directly
                         next_action = selected_action_name
                else:
                     console.print("[bold red]Error:[/bold red] Inline mode selected, but no command found in response.")
                     console.print("[dim]Raw Response:[/]", style="dim")
                     console.print(parsed_output.get('raw', 'N/A'), style="dim")
                     sys.exit(1)

            # --- Handle Chosen Action ---
            if next_action == 'execute':
                if last_command:
                    execute_command(last_command)
                    break # Exit loop after execution
                else:
                    console.print("[yellow]No command available to execute.[/]")
                    if Confirm.ask(Text.from_markup("Refine the query instead ([bold underline]R[/]efine)?"), default=True, console=console):
                        next_action = 'refine' # Fall through to refine
                    else:
                        break

            elif next_action == 'modify':
                if last_command:
                    modified_cmd = modify_command_interactive(last_command)
                    if modified_cmd:
                        if Confirm.ask(f"Execute modified command?\n$ {modified_cmd}", default=True, console=console):
                            execute_command(modified_cmd)
                            break # Exit loop after executing modified cmd
                        else:
                            console.print("Modified command not executed.")
                            if Confirm.ask(Text.from_markup("Refine the original query further ([bold underline]R[/]efine)?"), default=False, console=console):
                                 next_action = 'refine' # Fall through
                            else:
                                 break
                    else:
                         # Modification cancelled or cleared
                         if Confirm.ask(Text.from_markup("Refine the original query further ([bold underline]R[/]efine)?"), default=False, console=console):
                             next_action = 'refine' # Fall through
                         else:
                             break
                else:
                    console.print("[yellow]No command available to modify.[/]")
                    if Confirm.ask(Text.from_markup("Refine the query instead ([bold underline]R[/]efine)?"), default=True, console=console):
                        next_action = 'refine' # Fall through
                    else:
                        break

            # Handle Refine Action (must come after execute/modify might set it)
            if next_action == 'refine':
                try:
                    refinement_query = Prompt.ask("\nRefine your request (or press Enter to quit)", default="", console=console)
                    if refinement_query.strip():
                        current_query = refinement_query.strip()
                        last_command = None # Clear last command for new turn
                        console.print("-" * 20) # Visual separator
                        continue # Go to start of loop
                    else:
                        console.print("Exiting.")
                        break
                except (EOFError, KeyboardInterrupt):
                     console.print("\nExiting.")
                     break

            elif next_action == 'copy':
                 # Fully handled within the inline prompt logic or TUI exit logic.
                 # If TUI copy happened, prompt for next step.
                 if output_mode == 'tui':
                     # Ask again what to do after TUI copy (excluding copy)
                     post_tui_copy_actions = list(base_inline_actions)
                     post_tui_copy_actions.append(quit_action)
                     post_tui_copy_prompt, post_tui_copy_choices = create_action_prompt(post_tui_copy_actions)
                     post_tui_copy_map = {letter.lower(): full_name for letter, full_name, _ in post_tui_copy_actions}

                     action_after_tui_copy_letter = Prompt.ask(
                         post_tui_copy_prompt,
                         choices=post_tui_copy_choices,
                         default="q", console=console, show_choices=False
                     ).lower()
                     next_action_after_tui_copy = post_tui_copy_map.get(action_after_tui_copy_letter)

                     # Re-route based on choice after TUI copy
                     if next_action_after_tui_copy == 'execute': next_action = 'execute'; continue
                     if next_action_after_tui_copy == 'modify': next_action = 'modify'; continue
                     if next_action_after_tui_copy == 'refine': next_action = 'refine'; continue
                     # Otherwise (quit) fall through

                 # If inline copy, next_action was already updated. Loop continues.


            elif next_action is None or next_action == 'quit': # Handles TUI quit (None) or explicit 'quit'
                console.print("Exiting.")
                break

            else:
                 console.print(f"[yellow]Warning:[/yellow] Unknown action '{next_action}' received. Exiting.")
                 break

        # --- Error Handling within the Loop ---
        except GeminiApiError as e:
            console.print(f"[bold red]Gemini API Error:[/]\n {e}")
            sys.exit(1)
        except OneQError as e:
             console.print(f"[bold red]Application Error:[/]\n {e}")
             sys.exit(1)
        except (EOFError, KeyboardInterrupt):
             console.print("\nOperation cancelled by user. Exiting.")
             sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred:[/]\n {e}")
            import traceback
            console.print(traceback.format_exc(), style="dim")
            sys.exit(1)

    sys.exit(0)


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