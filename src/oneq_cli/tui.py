# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

import sys
import re
from typing import Optional, Union, Dict, Any, Literal, List

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Label, Input, Button, Static, Markdown
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Horizontal

from . import history

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
        border: tall $primary 60%;
        padding: 2;
    }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE,tall=True)
        yield Container(
            Label(self.SUB_TITLE),
            Input(placeholder="Enter your API key", id="api_key_input"),
            Button("Save API Key", id="save_button", variant="primary"),
            Button("Cancel", id="cancel_button"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "save_button":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("Please enter an API key.", title="Error", severity="error", timeout=3.0)
        elif event.control.id == "cancel_button":
            self.exit(None)  # Signal cancellation


class ResponseAppResult:
    """Represents the result of the ResponseApp."""
    def __init__(self, action: str, command_text: Optional[str] = None):
        self.action = action
        self.command_text = command_text


class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the Gemini response and handle user actions."""
    TITLE = "1Q Response"
    SUB_TITLE = "Generated Command"
    CSS_PATH = None

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
    .body {
        layout: vertical;
        height: 100%;
    }
    .command_panel {
        height: auto;
        border: tall $secondary;
        margin: 1;
        padding: 1;
    }
    .button_panel {
        dock: bottom;
        height: auto;
        layout: horizontal;
        margin: 1;
    }
    Button {
        width: 1fr;
        margin: 0 1;
    }
    Markdown {
        height: 100%;
    }
    .history_panel {
        border: tall $secondary;
        margin: 1;
        padding: 1;
    }
    """

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")
        self.history: List[Dict[str, str]] = history.load_history() # Load history
        self.history_index: int = len(self.history) -1 #start at the end of history

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(title=self.TITLE, show_clock=True)
        with Container(classes="body"):
            yield Label(f"Query: {self.query_text}", id="query_label")
            yield Label("Command:", id="command_header")
            yield Static(self.command_text, id="command_text", classes="command_panel")
            with Container(classes="history_panel"):
                yield Label("History", id="history_header")
                yield Label(self.get_current_history_entry(), id="history_text")
            with Container(classes="button_panel"):
                yield Button("Execute", id="execute_button", variant="primary")
                yield Button("Copy", id="copy_button")
                yield Button("Modify", id="modify_button")
                yield Button("Refine", id="refine_button")
                yield Button("Prev", id="prev_button")
                yield Button("Next", id="next_button")
        yield Footer()

    def get_current_history_entry(self) -> str:
        if not self.history:
            return "No history available."

        if not 0 <= self.history_index < len(self.history):
            return "End of History"
        
        entry = self.history[self.history_index]
        return f"Query: {entry['query']}\nCommand: {entry['command']}"
    
    def on_mount(self) -> None:
        self.update_history_display()

    def update_history_display(self) -> None:
          """Updates the history display with the current history entry."""
          history_text = self.query_one("#history_text", Label)
          history_text.update(self.get_current_history_entry())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.control.id

        if button_id == "execute_button":
            self.action_execute_command()
        elif button_id == "copy_button":
            self.exit(ResponseAppResult("copy", self.command_text))
        elif button_id == "modify_button":
            self.action_modify_command()
        elif button_id == "refine_button":
            self.action_refine_query()
        elif button_id == "prev_button":
            if self.history_index > 0:
                self.history_index -= 1
                self.update_history_display()
        elif button_id == "next_button":
            if self.history_index < len(self.history) -1:
                self.history_index += 1
                self.update_history_display()

    def action_execute_command(self) -> None:
        """Exits the TUI