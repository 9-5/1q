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
    Vertical { width: auto; height: auto; border: tall $panel; padding: 2 4; }
    Input { width: 60; }
    Button { width: 100%; margin-top: 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header(title=self.TITLE, show_clock=True)
        with Vertical():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Paste your API key here", id="api_key_input")
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save", variant="primary")
            yield Button("Cancel", id="cancel")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "save":
            api_key = self.query_one(Input).value
            if api_key:
                try:
                    cli.config.save_api_key(api_key)
                    self.exit(api_key)  # Return the API key
                except Exception as e:
                    self.app.console.print(f"Error saving API key: {e}")
                    self.exit(None)
            else:
                self.app.console.print("API Key cannot be empty.")
        elif event.control.id == "cancel":
            self.exit(None)  # Return None if cancelled

def run_api_key_setup() -> Union[str, None]:
    """Runs the API Key setup TUI and returns the API key or None if cancelled."""
    app = ApiKeyApp()
    return app.run()

class ResponseScreen(Screen):
    """Screen for displaying the response and available actions."""

    def __init__(self, response_data: Dict[str, Any], name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None, disabled: bool = False):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")
        self.history_data: List[Dict[str, str]] = history.load_history()

    def compose(self) -> ComposeResult:
        yield Header(title="1Q Response", show_clock=True)
        yield Footer()

        with Container(classes="main_container"):
            with Vertical(classes="left_pane"):
                yield Label("Query:", style="bold")
                yield Static(self.query_text, id="query_text", classes="scrollable")
                yield Label("\nGenerated Command:", style="bold")
                yield Static(self.command_text, id="command_output", classes="scrollable")

            with Vertical(classes="right_pane"):
                yield Button("Execute Command", id="execute", variant="primary")
                yield Button("Modify Command", id="modify")
                yield Button("Refine Query", id="refine")
                yield Button("Copy Command", id="copy")


class ResponseApp(App[ResponseAppResult]):
    """Main app for displaying the response and handling actions."""

    CSS_PATH = None
    BINDINGS = [
        Binding("e", "execute_command", "Execute", key_display="E"),
        Binding("m", "modify_command", "Modify", key_display="M"),
        Binding("r", "refine_query", "Refine", key_display="R"),
        Binding("c", "copy_command", "Copy", key_display="C"),
        Binding("q", "quit", "Quit", key_display="Q"),
    ]

    def __init__(self, response_data: Dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.response_data = response_data
        self.query_text: str = response_data.get("query", "No query provided.")
        self.command_text: str = response_data.get("command", "No command generated.")
        self.history_data: List[Dict[str, str]] = history.load_history()

    def on_mount(self) -> None:
        self.push_screen(ResponseScreen(self.response_data))

    def action_quit(self) -> None:
         """Quits the TUI app."""
         self.exit()

    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return

        try:
            import pyperclip
            pyperclip.copy(self.command_text)
            self.notify("Command copied to clipboard!", title="Command Copied", severity="success", timeout=3.0)

        except ImportError:
            self.notify("pyperclip is not installed. Please install it to use the copy feature.", title="Copy Failed", severity="error", timeout=5.0)


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