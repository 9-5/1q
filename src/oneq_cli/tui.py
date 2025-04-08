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
        border: tall $primary;
        padding: 1;
    }

    Input {
        width: 60;
        margin-bottom: 1;
    }

    Button {
        width: 20;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(title=self.TITLE, show_clock=True)
        yield Footer()
        with Vertical():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste your API Key here", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            with Horizontal():
                yield Button("Save", id="save_button", variant="primary")
                yield Button("Cancel", id="cancel_button", variant="default")


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "save_button":
            api_key = self.query_one("#api_key_input", Input).value.strip()
            if api_key:
                self.exit(api_key)
            else:
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
    }

    Markdown {
        width: auto;
        height: auto;
        margin: 1;
        border: round $primary;
        padding: 1;
    }

    Horizontal {
        width: auto;
        height: auto;
        margin: 1;
    }

    Button {
        width: 16;
        margin: 1;
    }
    """

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.response_data = response_data
        self.query_text = response_data.get("query", "No query provided.")
        self.command_text = response_data.get("command", "No command generated.")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(title="1Q Response", show_clock=True)
        yield Footer()
        with Container():
            yield Label("[bold]Query:[/bold]")
            yield Markdown(f"```text\n{self.query_text}\n```")
            yield Label("[bold]Command:[/bold]")
            yield Markdown(f"```bash\n{self.command_text}\n```")

            with Horizontal():
                yield Button("Execute", id="execute_button", variant="primary")
                yield Button("Copy", id="copy_button", variant="primary")
                yield Button("Modify", id="modify_button", variant="default")
                yield Button("Refine Query", id="refine_button", variant="default")


    async def on_mount(self) -> None:
        """Save the interaction to history after the TUI is mounted."""
        history.save_history(self.query_text, self.command_text) # Save to history

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        if event.button.id == "copy_button":
            self.exit("copy")

        elif event.button.id == "execute_button":
         if not self.command_text:
             self.notify("No command to execute.", title="Execution Failed", severity="warning", timeout=3.0)
             return
        self.exit("execute")

    def action_modify_command(self) -> None:
        """Exits the TUI signalling to