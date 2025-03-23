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
    Vertical { width: auto; height: auto; }
    Container { width: auto; height: auto; padding: 1 2; }
    Input { width: 60; }
    Button { width: 15; margin-top: 1; }
    Label { margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        with Container():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste API Key here", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save", id="save_key", variant="primary")
            yield Button("Cancel", id="cancel_key")
        yield Footer()


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id == "save_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)  # Return the API key
            else:
                self.notify("API Key cannot be empty!", title="Error", severity="error", timeout=3.0)
        elif button_id == "cancel_key":
            self.exit(None)  # Return None if cancelled

def run_api_key_setup() -> Optional[str]:
    """Runs the API Key setup TUI."""
    app = ApiKeyApp()
    return app.run() # type: ignore [return-value]

class ResponseAppResult:
    """Class to hold the result of the ResponseApp."""
    def __init__(self, action: Optional[str] = None, command_text: Optional[str] = None, error: Optional[str] = None) -> None:
        self.action = action
        self.command_text = command_text
        self.error = error

class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and allow actions."""
    TITLE = "1Q - Response"
    SUB_TITLE = "Review, Execute, or Modify"
    CSS_PATH = None
    BINDINGS = [
        Binding("escape", "app.quit", "Quit"),
        Binding("e", "execute_command", "Execute", show=True),
        Binding("m", "modify_command", "Modify", show=True),
        Binding("r", "refine_query", "Refine", show=True),
    ]
    CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    #response_container {
        layout: vertical;
        height: 100%;
    }

    #explanation {
        margin: 1;
    }

    #command {
        margin: 1;
        background: $panel;
        padding: 1;
    }

    #error_log {
        margin: 1;
        background: $error;
        color: white;
        padding: 1;
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
            yield Static(self.command_text, id="command", markup