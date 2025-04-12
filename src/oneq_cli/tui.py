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
    Vertical { width: auto; height: auto; border: tall $panel; padding: 2; }
    Input { width: 60; }
    Button { margin-top: 2; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, subtitle=self.SUB_TITLE)
        with Vertical():
            input = Input(placeholder="Your API Key", password=True)
            input.focus()
            yield input
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            api_key = self.query_one(Input).value.strip()
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty.", title="Error", severity="error", timeout=3.0)
        else:
            self.exit(None) # Signal cancelled


def ask_for_api_key() -> Union[str, None]:
    """Runs the ApiKeyApp and returns the entered API key or None if cancelled."""
    app = ApiKeyApp()
    return app.run()

ResponseAppResult = Union[Literal["execute"], Literal["modify"], Literal["refine"]]

class HistoryScreen(ModalScreen):
    """A popup screen to display command history."""

    def __init__(self, history_data: List[Dict[str, str]], name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None):
        super().__init__(name=name, id=id, classes=classes)
        self.history_data = history_data

    def compose(self) -> ComposeResult:
        yield Header(title="Command History",tall=False)
        history_text = ""
        for item in self.history_data:
            history_text += f"* **Query:** {item['query']}\n"
            history_text += f"  **Command:** {item['command']}\n\n"
        yield Markdown(history_text)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Markdown).scroll_visible() # Scroll to top.
        self.set_focus(self.query_one(Markdown))


class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the command and explanation, with action choices."""
    TITLE = "1Q Response"
    SUB_TITLE = "Review, Execute, or Modify"
    CSS_PATH = None
    CSS = """
    Screen {
        layout: vertical;
    }

    #response-container {
        height: 70%;
        border: tall $panel;
        margin: 1;
        padding: 1;
    }

    #query-label {
        margin-bottom: 1;
    }

    #explanation-markdown {
        margin-top: 1;
    }


    Footer {
        dock: bottom;
    }

    Button {
        width: 100%;
    }
    """

    def __init__(self, response_data: Dict[str, Any], name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None):
        super().__init__(name=name, id=id, classes=classes)
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
        yield Button("Modify Command", id="modify")
        yield Button("Refine Query", id="refine")
        yield Button("View History", id