# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

import sys
import re
from typing import Optional, Union, Dict, Any, Literal

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Label, Input, Button, Static, Markdown
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ApiKeyApp(App[Union[str, None]]):
    """TUI App to prompt for the Gemini API Key."""
    TITLE = "1Q API Key Setup"
    SUB_TITLE = "Enter your Google AI Studio API Key"
    CSS_PATH = None # Inline CSS below

    CSS = """
    Screen { align: center middle; }
    #dialog {
        grid-size: 2; grid-gutter: 1 2; grid-rows: auto auto auto;
        padding: 0 1; width: 60; height: auto; max-height: 80%;
        border: thick $accent; background: $surface;
    }
    Label { text-align: center; width: 100%; column-span: 2; }
    Input { column-span: 2; margin-bottom: 1; }
    #submit-button { width: 100%; column-span: 1; }
    #cancel-button { width: 100%; column-span: 2; }
    .error { color: red; }
    """

    api_key = reactive("")
    error_message = reactive("")

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.SUB_TITLE)
            yield Input(placeholder="Paste your API key here...", password=True, id="api-key-input")
            yield Label(self.error_message, id="error-label", classes="error")
            yield Button("Submit", variant="primary", id="submit-button")
            yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "api-key-input":
            self.api_key = event.value
            self.error_message = "" # Clear error

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
             self._submit_key()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-button":
            self._submit_key()
        elif event.button.id == "cancel-button":
            self.exit(None) # None indicates cancellation

    def _submit_key(self) -> None:
        trimmed_key = self.api_key.strip()
        if trimmed_key:
            self.exit(trimmed_key)
        else:
            self.error_message = "[bold red]API Key cannot be empty.[/]"
            self.query_one("#error-label", Label).update(self.error_message)


def prompt_for_api_key() -> Optional[str]:
    """Runs the ApiKeyApp and returns the entered key or None if cancelled."""
    app = ApiKeyApp()
    result = app.run()
    return result.strip() if isinstance(result, str) else None


ResponseAppResult = Optional[Literal["execute", "modify", "copy", "refine"]]

class ResponseApp(App[ResponseAppResult]):
    """Textual app to display the structured Gemini response and handle actions."""
    TITLE = "1Q Response"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("c", "copy_command", "Copy Cmd", show=True, key_display="c"),
        Binding("x", "execute_command", "Execute", show=True, key_display="x"),
        Binding("m", "modify_command", "Modify", show=True, key_display="m"),
        Binding("r", "refine_query", "Refine", show=True, key_display="r"),
    ]

    CSS = """
    Screen { padding: 1; }
    VerticalScroll { border: round $accent; padding: 0 1; }
    Markdown { margin-bottom: 1; }
    #install-display { border-top: thick $accent; padding-top: 1; }
    #explanation-display { border-top: thick $accent; padding-top: 1; }
    """

    def __init__(self, response_data: Dict[str, Any]):
        super().__init__()
        self.response_data = response_data
        raw_command = response_data.get('command')

        # Filter markdown code blocks from command before displaying/copying
        filtered_command = raw_command
        if raw_command:
            code_block_pattern = r'^```[^\n]*\n?(.*?)\n?```$'
            match = re.search(code_block_pattern, raw_command, re.DOTALL)
            if match:
                content = match.group(1).strip()
                filtered_command = content if content else None

        self.command_text = filtered_command # Store filtered command for actions

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            # Command (uses filtered text)
            if self.command_text:
                # Use ```bash for Markdown syntax highlighting hint
                command_md = f"### COMMAND\n```bash\n{self.command_text}\n```"
                yield Markdown(command_md, id="command-display")
            else:
                 yield Static("[yellow]No command generated in this response.[/]", id="command-display")

            # Installation
            if self.response_data.get('install'):
                 install_md = f"### INSTALLATION\n\n{self.response_data['install']}"
                 yield Markdown(install_md, id="install-display")

            # Explanation
            if self.response_data.get('explanation'):
                explanation_md = f"### EXPLANATION\n\n{self.response_data['explanation']}"
                yield Markdown(explanation_md, id="explanation-display")

        yield Footer()

    def action_copy_command(self) -> None:
        """Copies the (filtered) command text to the clipboard and exits."""
        if not self.command_text:
             self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
             return
        try:
            self.app.clipboard = self.command_text # Copy filtered command
            self.notify("Command copied!", title="Copied!", severity="information", timeout=3.0)
            self.exit("copy") # Exit with 'copy' action
        except Exception as e:
             self.notify(f"Error copying: {e}", title="Copy Failed", severity="error", timeout=5.0)
             # Optionally suggest installing clipboard tools
             # if sys.platform == "linux" or sys.platform == "darwin":
             #     self.notify("Tip: Install 'wl-copy', 'xclip'/'xsel', or 'pbcopy'.", timeout=7.0)

    def action_execute_command(self) -> None:
        """Exits the TUI signalling to execute the command."""
        if not self.command_text:
             self.notify("No command to execute.", title="Execute Failed", severity="warning", timeout=3.0)
             return
        self.exit("execute")

    def action_modify_command(self) -> None:
        """Exits the TUI signalling to modify the command."""
        if not self.command_text:
             self.notify("No command to modify.", title="Modify Failed", severity="warning", timeout=3.0)
             return
        self.exit("modify")

    def action_refine_query(self) -> None:
        """Exits the TUI signalling to refine the query."""
        self.exit("refine")


def display_response_tui(response_data: Dict[str, Any]) -> ResponseAppResult:
    """Runs the ResponseApp and returns the chosen action."""
    app = ResponseApp(response_data=response_data) # Filtering happens in __init__
    result = app.run()
    return result