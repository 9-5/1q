# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

import sys
import re
from typing import Optional, Union, Dict, Any, Literal, List

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll, Horizontal
from textual.widgets import Header, Footer, Label, Input, Button, Static, Markdown, ListItem, ListView
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from . import history


class ApiKeyApp(App[Union[str, None]]):
    """TUI App to prompt for the Gemini API Key."""
    TITLE = "1Q API Key Setup"
    SUB_TITLE = "Enter your Google AI Studio API Key"
    CSS_PATH = None # Inline CSS below

    CSS = """
    Screen { align: center middle; }
    Vertical { width: auto; height: auto; border: tall $primary; padding: 2; }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.TITLE, id="title"),
            Label(self.SUB_TITLE, id="subtitle"),
            Input(placeholder="Paste your API key here", id="api-key-input"),
            Button("Save", id="save-button", variant="primary"),
            Button("Cancel", id="cancel-button"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            api_key = self.query_one(Input).value.strip()
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API key cannot be empty.", title="Error", severity="error", timeout=2.0)
        elif event.button.id == "cancel-button":
            self.exit(None) # Signal Cancel


class ResponseAppResult:
    """
    A simple data class to hold the results from the ResponseApp.
    Allows for more structured handling of the app's output.
    """

    def __init__(self, action: Optional[str] = None, command: Optional[str] = None, query: Optional[str] = None):
        self.action = action
        self.command = command
        self.query = query


class ResponseApp(App[ResponseAppResult]):
    """
    A Textual app to display the response and handle user actions.
    """

    CSS_PATH = None  # Override default CSS
    BINDINGS = [
        Binding("c", "copy_command", "Copy", show=True),
        Binding("e", "execute_command", "Execute", show=True),
        Binding("m", "modify_command", "Modify", show=True),
        Binding("r", "refine_query", "Refine", show=True),
        Binding("h", "view_history", "History", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.response_data = response_data
        self.query_text: str = response_data.get("query", "")
        self.command_text: str = response_data.get("command", "")
        self.full_response_text: str = f"Query:\n{self.query_text}\n\nCommand:\n{self.command_text}"

    def compose(self) -> ComposeResult:
        """Compose the UI elements."""
        yield Header(title="1Q Response",tall=False)
        with Container(id="main_content"):
            yield Static(self.full_response_text, id="response-text", markup=False)
        yield Footer()

    def action_copy_command(self) -> None:
        """Exits the TUI signalling to copy the command."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return
        self.exit("copy")

    def action_execute_command(self) -> None:
        """Exits the TUI signalling to execute the command."""
        if not self.command_text:
             self.notify("No command to execute.", title="Execution Failed", severity="warning", timeout=3.0)
             return