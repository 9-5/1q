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

ResponseAppResult = Dict[str, str]

class ApiKeyApp(App[Union[str, None]]):
    """TUI App to prompt for the Gemini API Key."""
    TITLE = "1Q API Key Setup"
    SUB_TITLE = "Enter your Google AI Studio API Key"
    CSS_PATH = None # Inline CSS below

    CSS = """
    Screen { align: center middle; }

    Container {
        width: auto;
        height: auto;
        border: round $primary 2;
        padding: 2 4;
        layout: vertical;
    }

    Input {
        width: 60;
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(title=self.TITLE,tall=False)
        with Container():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste your API key here", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save_api_key", variant="primary")
            yield Button("Cancel", id="cancel", variant="default")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.control.id

        if button_id == "save_api_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("Please enter an API key.", title="Error", severity="error", timeout=2.0)
        elif button_id == "cancel":
            self.exit(None)

class ResponseApp(App[ResponseAppResult]):
    """Textual app to display the Gemini API response."""

    TITLE = "1Q - Response"
    BINDINGS = [
        Binding("c", "copy_command", "Copy Command", show=True),
        Binding("e", "execute_command", "Execute Command", show=True),
        Binding("m", "modify_command", "Modify Command", show=True),
        Binding("r", "refine_query", "Refine Query", show=True),
        Binding("q", "quit", "Quit", show=True)
    ]

    CSS = """
    #response_container {
        layout: vertical;
        height: 100%;
    }
    #explanation_header {
        margin-bottom: 0;
        padding: 0;
    }
    #explanation {
        margin-top: 0;
        padding: 1;
        height: 50%;
        border: tall $secondary 1;
    }
    #command_header {
        margin-bottom: 0;
        padding: 0;
    }
    #command {
        margin-top: 0;
        padding: 1;
        height: auto;
        border: tall $secondary 1;
        width: auto;
        overflow: auto;
    }
    """
    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.response_data = response_data
        self.command_text = response_data.get("command", "")
        self.explanation_text = response_data.get("explanation", "")
        self.error_message = response_data.get("error", "")  # Capture potential errors from the response

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(title=self.TITLE, show_clock=True)
        with Container(id="response_container"):
            yield Label("Explanation:", id="explanation_header")
            yield VerticalScroll(Markdown(self.explanation_text), id="explanation")
            yield Label("Command:", id="command_header")
            yield Static(self.command_text, id="command", markup=True, expand=True)
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted (ready to receive key presses)."""
        if self.error_message:
            self.notify(self.error_message, title="Error", severity="error", timeout=5.0)

    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return
        try:
            import pyperclip
            pyperclip.copy(self.command_text)
            self.notify("Command copied to clipboard!", title="Copied", timeout=2.0)
        except ImportError:
            self.notify("pyperclip not installed. Please install it to copy commands.", title="Copy Failed", severity="error", timeout=3.0)

    def action_execute_command(self) -> None:
        """Exits the TUI signalling to execute the command."""
        if not self.command_text:
             self.notify("No command to execute.", title="Execution Failed", severity="warning", timeout=3.0)
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