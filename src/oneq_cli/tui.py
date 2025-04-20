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
        border: tall $panel;
        padding: 1 2;
    }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        yield Footer()
        with Vertical():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste your API key here", id="api_key_input")
            yield api_key_input
            yield Button("Save API Key", id="save_api_key", variant="primary")


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "save_api_key":
            api_key = self.query_one(Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty!", severity="error", timeout=3.0)


class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and options."""
    CSS_PATH = None
    TITLE = "1Q - Response"
    SUB_TITLE = "Review, Execute, or Modify"
    BINDINGS = [
        Binding("ctrl+e", "execute_command", "Execute", show=True),
        Binding("ctrl+m", "modify_command", "Modify", show=True),
        Binding("ctrl+r", "refine_query", "Refine", show=True),
        Binding("ctrl+c", "copy_command", "Copy", show=True),
        Binding("escape", "app.quit", "Quit", show=True),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }
    #header {
        dock: top;
    }
    #footer {
        dock: bottom;
    }

    .main_container {
        layout: horizontal;
        height: 1fr;
    }

    .left_pane {
        width: 50%;
        border-right: tall $primary-background;
        padding: 1;
    }

    .right_pane {
        width: 50%;
        padding: 1;
    }

    .scrollable {
        overflow-y: scroll;
        height: 100%;
    }

    Markdown {
        height: auto;
    }

    #command_output {
        margin-top: 1;
        padding: 1;
        border: tall $secondary;
    }

    .history_list_item {
        padding: 0;
        margin: 0;
    }

    ListView {
        border: tall $secondary;
    }
    """

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")
        self.history_data: List[Dict[str, str]] = history.load_history()


    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        yield Footer()

        with Container(classes="main_container"):
            with Vertical(classes="left_pane"):
                yield Label("Query:", style="bold")
                yield Static(self.query_text, id="query_text", classes="scrollable")
                yield Label("\nGenerated Command:", style="bold")
                yield Static(self.command_text, id="command_output", classes="scrollable")

            with Vertical(classes="right_pane"):
                yield