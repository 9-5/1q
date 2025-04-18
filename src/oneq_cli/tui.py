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
    Container {
        width: auto;
        height: auto;
        border: tall $primary;
        padding: 2 4;
    }
    Input { width: 60; }
    Button { margin-top: 2; }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the API key entry screen."""
        yield Header(title=self.TITLE, show_clock=True)
        with Container():
            yield Label(self.SUB_TITLE)
            api_key_input = Input(placeholder="Enter your API key here", id="api_key_input", password=True)
            api_key_input.focus()
            yield api_key_input
            yield Button("Save API Key", id="save_api_key", variant="primary")
            yield Button("Cancel", id="cancel", variant="default")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler for button presses."""
        button_id = event.button.id
        if button_id == "save_api_key":
            api_key = self.query_one("#api_key_input", Input).value
            if api_key:
                # Save the API key (implementation in config.py)
                config_manager = cli.config.ConfigManager()
                config_manager.config[cli.config.CREDENTIALS_SECTION][cli.config.API_KEY_CONFIG_KEY] = api_key
                try:
                    config_manager.save_config()
                    self.app.exit(api_key)  # Return the API key
                except cli.config.ConfigurationError as e:
                    self.app.exit(None) # Signal failure
                    self.app.notify(f"Failed to save API Key: {e}", title="Error", severity="error")
            else:
                self.app.notify("API Key cannot be empty!", title="Warning", severity="warning")

        elif button_id == "cancel":
            self.app.exit(None)  # Signal cancellation


def run_api_key_setup() -> Optional[str]:
    """Runs the API Key setup TUI and returns the entered key or None if cancelled."""
    app = ApiKeyApp()
    api_key = app.run()
    return api_key


class HistoryApp(App[Optional[Dict[str, str]]]):
    """A modal app to display command history."""

    CSS = """
    #history-list {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the history modal view."""
        history_data = history.load_history()
        list_items: List[ListItem] = []

        for item in history_data:
            query = item.get("query", "No query")
            command = item.get("command", "No command")
            list_items.append(ListItem(Label(f"[bold]{query}[/]\n[dim]{command}[/]", markup=True)))

        history_list = ListView(*list_items, id="history-list")
        yield Container(history_list)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle when an item is selected."""
        list_view = event.list_view
        selected_item = event.item

        # Find the index of the selected item
        item_index = list_view.children.index(selected_item)
        history_data = history.load_history()

        if 0 <= item_index < len(history_data):
            self.app.exit(history_data[item_index])
        else:
            self.app.exit(None)
            self.app.notify("Invalid history item selected.", title="Error", severity="error")


class ResponseApp(App[ResponseAppResult]):
    """The main TUI app to display the command and handle actions."""
    CSS_PATH = None # Inline CSS
    CSS = """
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
    }

    #query_box, #command_box {
        width: 50%;
        height: 100%;
        padding: 1;
        border: tall $secondary;
    }

    Vertical {
        width: 1fr;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("c", "copy_command", "Copy", show=True),
        Binding("e", "execute_command", "Execute", show=True),
        Binding("m", "modify_command", "Modify", show=True),
        Binding("r", "refine_query", "Refine", show=True),
        Binding("h", "show_history", "History", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, response_data: Dict[str, Any], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.query_text: Optional[str] = response_data.get("query")
        self.command_text: Optional[str] = response_data.get("command")
        self.action_taken: Optional[ResponseAppResult] = None # None, "execute", "modify", "refine"


    def on_mount(self) -> None:
        """Call after terminal is ready."""
        if not self.query_text:
            self.notify("No query received.", title="Missing Info", severity="warning", timeout=3.0)
        if not self.command_text:
            self.notify("No command generated.", title="Missing Info", severity="warning", timeout=3.0)


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
        selected_item = await self.view.dock_screen(history_app)

        if selected_item:
            self.query_text = selected_item.get("query")
            self.command_text = selected_item.get("command")
            # Refresh the display
            self.query_one("#query_box Markdown").update(self.query_text or "No query provided.")
            self.query_one("#command_box Markdown").update(self.command_text or "No command generated.")
            self.notify("History item loaded.", title="History", severity="success", timeout=2.0)
        else:
            self.notify("No history item selected.", title="History", severity="info", timeout=2.0)


    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if not self.command_text:
            self.notify("No command to copy.", title="Copy Failed", severity="warning", timeout=3.0)
            return

        if cli.PYPERCLIP_AVAILABLE:
            try:
                import pyperclip
                pyperclip.copy(self.command_text)
                self.notify("Command copied to clipboard!", title="Copied!", severity="success", timeout=2.0)
            except pyperclip.PyperclipException:
                self.notify("Copy failed. Ensure you have 'xclip' or 'xsel' installed.", title="Copy Error", severity="error", timeout=3.0)
        else:
            self.notify("pyperclip