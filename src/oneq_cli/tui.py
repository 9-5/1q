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
from ..oneq_cli import cli

ResponseAppResult = Optional[Literal["execute", "modify", "refine", "copy"]]

class ApiKeyApp(App[Union[str, None]]):
    """TUI App to prompt for the Gemini API Key."""
    TITLE = "1Q API Key Setup"
    SUB_TITLE = "Enter your Google AI Studio API Key"
    CSS_PATH = None # Inline CSS below

    CSS = """
    Screen { align: center middle; }
    Vertical { width: auto; height: auto; border: tall $panel; padding: 2; }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, subtitle=self.SUB_TITLE)
        with Vertical():
            yield Label("API Key:")
            api_key_input = Input(placeholder="Paste your API key here", id="api-key-input")
            api_key_input.focus()
            yield Button("Save", id="save-api-key", variant="primary")
            yield Button("Cancel", id="cancel-api-key")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "cancel-api-key":
            self.exit(None)
        elif event.control.id == "save-api-key":
            api_key = self.query_one("#api-key-input", Input).value
            # Basic validation (can add more sophisticated checks)
            if not api_key:
                self.notify("API Key cannot be empty.", title="Validation Error", severity="error", timeout=3.0)
                return
            self.exit(api_key)


class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and options."""

    TITLE = "1Q Response"
    SUB_TITLE = "Review and take action"
    CSS_PATH = None # Inline CSS

    CSS = """
    #response-container {
        layout: vertical;
        width: auto;
        height: auto;
        margin: 1;
        padding: 1;
        border: round $primary;
    }

    #query-label {
        margin-bottom: 1;
    }

    #command-label {
        margin-bottom: 1;
    }

    #explanation-markdown {
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
    }

    """

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        # Extract data, providing defaults
        self.query_text: str = response_data.get("query", "")
        self.command_text: str = response_data.get("command", "")
        self.explanation_text: str = response_data.get("explanation", "")

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, subtitle=self.SUB_TITLE)

        with Container(id="response-container"):
            yield Label(f"[bold]Query:[/]\n{self.query_text}", id="query-label")
            yield Label(f"[bold blue]Command:[/]\n{self.command_text}", id="command-label")
            yield Markdown(f"[bold]Explanation:[/]\n{self.explanation_text}", id="explanation-markdown")

        yield Button("Execute Command", id="execute")
        yield Button("Copy Command", id="copy")
        yield Button("Modify Command", id="modify")
        yield Button("Refine Query", id="refine")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.control.id

        if button_id == "execute":
            self.action_execute_command()
        elif button_id == "modify":
            self.action_modify_command()
        elif button_id == "refine":
            self.action_refine_query()
        elif button_id == "copy":
            self.action_copy_command()

    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return

        if cli.copy_to_clipboard(self.command_text):
            self.exit("copy")  # Signal copy was successful.
        else:
            # copy_to_clipboard handles the notification on failure, so no need to repeat it here.
            pass


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