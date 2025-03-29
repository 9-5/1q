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

ResponseAppResult = Optional[Literal["copy", "execute", "modify", "refine"]]

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
        border: tall $primary;
        padding: 2;
    }
    Input { width: 60; }
    Button { width: 100%; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, subtitle=self.SUB_TITLE)
        yield Container(
            Label("API Key:"),
            Input(placeholder="Paste your Google AI Studio API Key here", id="api-key-input"),
            Button("Save", id="save-api-key", variant="primary"),
            Button("Cancel", id="cancel-api-key")
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id == "save-api-key":
            api_key = self.query_one("#api-key-input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("Please enter an API key.", title="Error", severity="error")
        elif button_id == "cancel-api-key":
            self.exit(None)


class ResponseApp(App[ResponseAppResult]):
    """Textual app to display the command and offer actions."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #response-area {
        height: 70%;
        border: tall $secondary;
        margin: 1;
    }

    #button-area {
        height: 10%;
        layout: horizontal;
        margin: 1;
    }

    Button {
        width: 20%;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("c", "copy", "Copy to Clipboard", show=True),
        Binding("e", "execute", "Execute", show=True),
        Binding("m", "modify_command", "Modify", show=True),
        Binding("r", "refine_query", "Refine Query", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.command_text: str = response_data.get("command", "")
        self.explanation_text: str = response_data.get("explanation", "")
        self.notes_text: str = response_data.get("notes", "")
        self.response_data = response_data # Keep the raw response for now.

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(title="1Q Response", show_clock=True)

        with Container(id="response-area"):
            yield Static(f"[bold]Command:[/]\n{self.command_text}", id="command-output")
            yield Static(f"[bold]Explanation:[/]\n{self.explanation_text}", id="explanation-output")
            yield Static(f"[bold]Notes:[/]\n{self.notes_text}", id="notes-output")

        with Container(id="button-area"):
            yield Button("Copy", id="copy-button", binding_key="c")
            yield Button("Execute", id="execute-button", binding_key="e")
            yield Button("Modify", id="modify-button", binding_key="m")
            yield Button("Refine Query", id="refine-query-button", binding_key="r")


        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id == "copy-button":
            self.action_copy()
        elif button_id == "execute-button":
            self.action_execute()
        elif button_id == "modify-button":
            self.action_modify_command()
        elif button_id == "refine-query-button":
            self.action_refine_query()

    def action_copy(self) -> None:
        """Exits the TUI signalling to copy the command."""
        if not self.command_text:
             self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
             return
        self.exit("copy")

    def action_execute(self) -> None:
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