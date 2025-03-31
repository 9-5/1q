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
    Container {
        width: auto;
        height: auto;
        border: round $primary 2;
        padding: 2 4;
    }
    Input { width: 60; }
    Button { margin-top: 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        yield Container(
            Label(self.SUB_TITLE),
            Input(placeholder="Paste your API key here", id="api_key_input"),
            Button("Save API Key", id="save_api_key", variant="primary"),
            Button("Cancel", id="cancel", variant="default"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "save_api_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                try:
                    from . import config
                    config.set_api_key(api_key)
                    self.exit(api_key)  # Return the API key
                except Exception as e:
                    self.exit(None) # Exit without key
                    self.app.exit()
            else:
                self.notify("Please enter an API key.", title="Error", severity="error")
        elif event.control.id == "cancel":
            self.exit(None)  # Return None if cancelled

    def on_mount(self) -> None:
        self.query_one(Header).tall = True


def run_api_key_setup() -> Union[str, None]:
    """Runs the API Key setup TUI and returns the entered key or None if cancelled."""
    app = ApiKeyApp()
    result = app.run()
    return result


class ResponseApp(App[Optional[Literal["copy", "execute", "modify", "refine"]]]):
    """TUI App to display the AI response and available actions."""
    TITLE = "1Q - Response"
    CSS_PATH = None # Inline CSS
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
    #response_container {
        width: 100%;
        height: 100%;
        margin: 1;
    }
    #query_label {
        width: 100%;
        margin-bottom: 1;
        padding: 1;
        border: tall $secondary 1;
    }

    #command_markdown {
        width: 100%;
        height: 100%;
        overflow: auto;
        padding: 1;
        border: tall $primary 1;
    }

    Button {
        margin: 1;
    }

    VerticalScroll {
        width: auto;
        height: auto;
    }
    """

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")
        self.response_data = response_data

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(title=self.TITLE, show_clock=True)
        with Container(id="response_container"):
            yield Label(f"Query: {self.query_text}", id="query_label")
            yield Markdown(f"```bash\n{self.command_text}\n```", id="command_markdown")

        yield Footer()

        yield Button("Copy to Clipboard", id="copy_button", binding="c", variant="primary")
        yield Button("Execute", id="execute_button", binding="e", variant="success")
        yield Button("Modify", id="modify_button", binding="m", variant="warning")
        yield Button("Refine Query", id="refine_button", binding="r")

        self.bind("c", "copy_command", "Copy", show=False)
        self.bind("e", "execute_command", "Execute", show=False)
        self.bind("m", "modify_command", "Modify", show=False)
        self.bind("r", "refine_query", "Refine", show=False)

    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return

        try:
            import pyperclip
            pyperclip.copy(self.command_text)
            self.notify("Command copied to clipboard!", title="Copied!", severity="success", timeout=3.0)
        except ImportError:
            self.notify(
                "pyperclip not installed. Please install it to use the copy feature.",
                title="Copy Failed",
                severity="error",
                timeout=5.0,
            )

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