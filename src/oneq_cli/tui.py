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
        border: tall $primary;
        padding: 2;
    }

    Input {
        width: auto;
        height: auto;
        margin-top: 1;
        margin-bottom: 2;
    }

    Button {
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, subtitle=self.SUB_TITLE)
        yield Label("Please enter your Google AI Studio API key:")
        input = Input(placeholder="Enter API Key", id="api_key_input")
        input.focus()
        yield input
        yield Horizontal(
            Button("Save", id="save_button", variant="primary"),
            Button("Cancel", id="cancel_button", variant="default"),
            width="auto",
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_button":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.query_one("#api_key_input", Input).focus() # Refocus the input if empty
                self.notify("API Key cannot be empty!", title="Error", severity="error", timeout=3.0)

        elif event.button.id == "cancel_button":
            self.exit(None)

def run_api_key_setup() -> Optional[str]:
    """Runs the ApiKeyApp and returns the API key or None if cancelled."""
    app = ApiKeyApp()
    api_key = app.run()
    return api_key

ResponseAppResult = Optional[Literal["execute", "copy", "modify", "refine"]]

class ResponseApp(App[ResponseAppResult]):
    """
    TUI App to display the response and available actions.
    """
    CSS_PATH = None # Inline CSS
    CSS = """
    Screen {
        layout: vertical;
    }

    Container {
        align: center top;
        width: auto;
        height: auto;
        margin: 1;