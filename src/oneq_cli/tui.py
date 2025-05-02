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
    Container {
        width: auto;
        height: auto;
        border: tall $primary 60%;
        padding: 2;
    }
    Input { width: 60; }
    Button { margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE,tall=False)
        with Container():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Enter your API key", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save_api_key", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.control.id == "save_api_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)  # Return the API key to the caller
            else:
                self.notify("API Key cannot be empty!", title="Error", severity="error", timeout=3.0)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
         api_key = self.query_one("#api_key_input", Input).value
         if api_key:
             self.exit(api_key)
         else:
             self.notify("API Key cannot be empty!", title="Error", severity="error", timeout=3.0)


def run_api_key_setup() -> Union[str, None]:
    """Runs the ApiKeyApp and returns the entered API key or None if cancelled."""
    app = ApiKeyApp()
    api_key = await app.run_async()
    return api_key


ResponseAppResult = Union[Literal["copy", "execute", "modify", "refine"], None]

class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and offer actions."""
    CSS_PATH = None
    BINDINGS = [
        Binding("c", "copy_command", "Copy Command", show=True),
        Binding("e", "execute_command", "Execute Command", show=True),
        Binding("m", "modify_command", "Modify Command", show=True),
        Binding("r", "refine_query", "Refine Query", show=True),
        Binding("q", "quit", "Quit", show=True)
    ]

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.query_text = response_data.get("query", "No query provided.")
        self.command_text = response_data.get("command", "No command generated.")
        self.full_response_text = response_data.get("full_response", "No response from the AI.")

    CSS = """
    #main_content {
        layout: vertical;
        width: 100%;
        height: 100%;
        overflow-y: auto;
        padding: 1;
    }

    #response-text {
        width: auto;
        height: auto;
        margin: 1;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
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