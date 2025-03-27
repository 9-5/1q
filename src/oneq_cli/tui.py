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
    Vertical {
        width: auto;
        height: auto;
        layout: vertical;
        border: tall $panel;
        padding: 1;
    }
    Input {
        width: 60;
        margin-bottom: 1;
    }
    Button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste API Key here", id="api-key-input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save-api-key", variant="primary")
            yield Button("Cancel", id="cancel", variant="default")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.control.id

        if button_id == "save-api-key":
            api_key = self.query_one("#api-key-input", Input).value
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty.", title="Input Error", severity="error", timeout=3.0)
        elif button_id == "cancel":
            self.exit(None)


def get_gemini_api_key_from_tui() -> Optional[str]:
    """Launches a Textual app to get the Gemini API key from the user."""
    app = ApiKeyApp()
    api_key = app.run()
    return api_key


class ResponseApp(App[Union[Literal["execute", "modify", "refine", "copy"], None]]):
    """TUI App to display the response and available actions."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #command-container {
        border: tall $secondary;
        margin: 1;
        padding: 1;
    }

    #explanation-container {
        border: tall $primary;
        margin: 1;
        padding: 1;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("a", "execute", "Execute Command", show=True),
        Binding("m", "modify_command", "Modify Command", show=True),
        Binding("r", "refine_query", "Refine Query", show=True),
        Binding("c", "copy_command", "Copy Command", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]


    def __init__(self, response_data: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.response_data = response_data
        self.command_text: str = response_data.get("command", "")
        self.explanation_text: str = response_data.get("explanation", "")
        self.user_query: str = response_data.get("query", "")  #If we start passing the query


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(title="1Q Response", subtitle="Review and Actions")
        with Container(id="command-container"):
            yield Label("Command:", style="bold")
            yield Markdown(f"```bash\n{self.command_text}\n```")

        with Container(id="explanation-container"):
            yield Label("Explanation:", style="bold")
            yield Label(self.explanation_text)

        yield Button("Execute Command", id="execute", variant="primary")
        yield Button("Modify Command", id="modify", variant="warning")
        yield Button("Refine Query", id="refine", variant="default")
        yield Button("Copy Command", id="copy", variant="default")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.control.id
        if button_id == "execute":
            self.action_execute()
        elif button_id == "modify":
            self.action_modify_command()
        elif button_id == "refine":
            self.action_refine_query()
        elif button_id == "copy":
            self.action_copy_command()

    def action_copy_command(self) -> None:
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