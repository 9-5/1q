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
from ..oneq_cli import cli

ResponseAppResult = Optional[Literal["execute", "modify", "refine", "copy"]]

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
        border: tall $primary;
        padding: 1 2;
    }
    Input { width: 60; }
    Button { width: 100%; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        yield Footer()
        with Vertical():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste your API key here", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save", style="success")
            yield Button("Cancel", id="cancel", style="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "cancel":
            self.exit(None)
        elif event.control.id == "save":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty!", title="Error", severity="error", timeout=3.0)

def run_api_key_setup() -> Union[str, None]:
    """Runs the ApiKeyApp and returns the entered API key or None if cancelled."""
    app = ApiKeyApp()
    result = app.run()
    return result

class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and available actions."""
    CSS_PATH = None # Inline CSS
    TITLE = "1Q - Response"
    SUB_TITLE = "Review the generated command"

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
    #query_container {
        height: auto;
        margin: 1;
    }
    #command_container {
        height: auto;
        margin: 1;
    }
    #explanation_container {
        height: 1fr;
        margin: 1;
    }
    Markdown {
        padding: 1;
    }
    Button {
        width: 100%;
    }
    VerticalScroll {
        border: tall $secondary;
    }
    """

    query_text: reactive[str] = reactive("")
    command_text: reactive[str] = reactive("")
    explanation_text: reactive[str] = reactive("")

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        # Initialize reactive variables from the provided data. This is done in init
        # because reactive variables need to be initialized on the class.
        self.query_text = response_data.get("query", "")
        self.command_text = response_data.get("command", "")
        self.explanation_text = response_data.get("explanation", "")

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        yield Footer()

        with Container(id="query_container"):
            yield Label("[bold]Query:[/bold]")
            yield Markdown(self.query_text or "No query provided.")

        with Container(id="command_container"):
            yield Label("[bold]Command:[/bold]")
            yield Markdown(f"```shell\n{self.command_text or 'No command generated.'}\n```")

        with Container(id="explanation_container"):
            yield Label("[bold]Explanation:[/bold]")
            explanation = self.explanation_text or "No explanation provided."
            yield VerticalScroll(Markdown(explanation))

        yield Button("Execute Command", id="execute", style="success")
        yield Button("Modify Command", id="modify", style="primary")
        yield Button("Refine Query", id="refine", style="warning")
        yield Button("