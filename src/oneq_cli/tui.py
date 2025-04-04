# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

import sys
import re
from typing import Optional, Union, Dict, Any, Literal, List

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll, Horizontal
from textual.widgets import Header, Footer, Label, Input, Button, Static, Markdown
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
    Vertical {
        width: auto;
        height: auto;
        layout: vertical;
        border: tall $primary 6;
        padding: 2 4;
    }
    Input { width: 60; }
    Button { margin-top: 2; }
    """

    def compose(self) -> ComposeResult:
        """Compose the layout of the API Key setup screen."""
        yield Header()
        yield Vertical(
            Label("Please enter your Google AI Studio API key:"),
            Input(placeholder="Enter API Key Here", id="api_key_input"),
            Button("Save", id="save_button", variant="primary"),
            Button("Cancel", id="cancel_button"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler for button presses."""
        button_id = event.button.id
        if button_id == "save_button":
            api_key = self.query_one(Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty!", title="Error", severity="error")
        elif button_id == "cancel_button":
            self.exit(None) # Signal Cancelled

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Event handler for submitting the input field (pressing Enter)."""
        api_key = event.value
        if api_key:
            self.exit(api_key)
        else:
            self.notify("API Key cannot be empty!", title="Error", severity="error")


def run_api_key_setup() -> Union[str, None]:
    """Runs the API Key setup TUI and returns the entered API Key, or None if cancelled."""
    app = ApiKeyApp()
    api_key = app.run()
    return api_key

class ResponseAppResult:
    """Represents the result of the ResponseApp, including the chosen action and command."""
    def __init__(self, action: str, command: str):
        self.action = action
        self.command = command

class ResponseApp(App[ResponseAppResult]):
    """Textual app to display the response and handle actions."""
    CSS_PATH = None # Inline CSS
    CSS = """
    Screen {
        layout: vertical;
    }

    #header {
        dock: top;
        height: 3;
        border-bottom: tall $primary;
    }

    #footer {
        dock: bottom;
        height: 3;
        border-top: tall $primary;
    }
    #body {
        layout: vertical;
        padding: 1;
        height: auto;
        width: 100%;
        overflow-y: scroll;

    }
    .horizontal-buttons {
        layout: horizontal;
        width: 100%;
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        align: center middle;
    }

    .button-container {
        width: auto;
        height: auto;
        margin-left: 1;
        margin-right: 1;
    }
    #response_text {
        width: auto;
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        padding: 1;
        border: tall $secondary;
    }

    #command_text {
        width: auto;
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        padding: 1;
        border: tall $secondary;
    }

    Button {
        width: auto;
    }

    .history-display {
      border: tall $secondary;
      padding: 1;
      margin-top: 1;
      margin-bottom: 1;
    }
    """
    TITLE = "1Q Response"
    SUB_TITLE = "Review and Take Action"
    BINDINGS = [
        Binding("ctrl+e", "execute_command", "Execute", show=True),
        Binding("ctrl+c", "copy_command", "Copy", show=True),
        Binding("ctrl+m", "modify_command", "Modify", show=True),
        Binding("ctrl+r", "refine_query", "Refine", show=True),
        Binding("escape", "quit", "Quit", show=True),
    ]

    def __init__(self