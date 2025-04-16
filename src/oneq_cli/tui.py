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
    Vertical { width: auto; height: auto; border: tall $primary; padding: 2; }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("Please enter your Google AI Studio API key:")
            api_key_input = Input(placeholder="Paste API Key here", id="api_key_input")
            yield api_key_input
            yield Button("Save API Key", id="save_api_key", variant="primary")
        yield Footer()


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_api_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty.", title="Error", severity="error", timeout=3.0)


class HistoryApp(App[Optional[Dict[str, str]]]):
    """A Textual app to display and select from command history."""

    CSS = """
    #history-list {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.history_items: List[Dict[str, str]] = history.load_history()

    def compose(self) -> ComposeResult:
        yield Header(title="Command History")
        history_list = ListView(id="history-list")

        for item in self.history_items:
            history_list.append(ListItem(Label(item["query"]), id=item["query"]))

        yield history_list
        yield Footer()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Called when the user clicks a list item."""
        selected_query = event.item.id
        selected_item = next((item for item in self.history_items if item["query"] == selected_query), None)
        self.exit(selected_item)

class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and allow actions."""

    CSS_PATH = None
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

    #content {
        layout: horizontal;
        height: auto;
        width: 100%;
    }
    #query_box {
        width: 50%;
        border-right: tall $secondary;
        padding: 1;
    }

    #command_box {
        width: 50%;
        padding: 1;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
    }

    """

    BINDINGS = [
        Binding("e", "execute_command", "Execute", show=True),
        Binding("m", "modify_command", "Modify", show=True),
        Binding("r", "refine_query", "Refine", show=True),
        Binding("c", "copy_command", "Copy", show=True),
        Binding("h", "show_history", "History", show=True),
    ]

    def __init__(self, response_data: Dict[str, Any], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")


    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(title="1Q Response", id="header")
        with Container(id="content"):
            with Vertical(id="query_box"):
                yield Label("[bold]Query:[/bold]")
                yield Markdown(self.query_text or "No query provided.")
            with Vertical(id="command_box"):
                yield Label("[bold]Command:[/bold]")
                yield Markdown(self.command_text or "No command generated.")
        yield Footer()


    async def action_show_history(self) -> None:
        """Show command history in a modal dialog."""
        history_app = HistoryApp()
        selected_item = await self.view.dock_screen