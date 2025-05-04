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

class HistoryBrowser(ModalScreen):
    """A modal screen to display command history."""

    def __init__(self, history_data: List[Dict[str, str]], name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None):
        super().__init__(name=name, id=id, classes=classes)
        self.history_data = history_data

    def compose(self) -> ComposeResult:
        yield Header(title="Command History",tall=False)
        yield Footer()
        with VerticalScroll(id="history-container"):
            for entry in self.history_data:
                yield Static(f"[bold]Query:[/bold] {entry['query']}\n[bold]Command:[/bold] {entry['command']}\n{'-'*20}", style="bright_white", id="history-entry")
        yield Horizontal(
            Button("Close", variant="primary", id="close-history"),
            Button("Execute", id="execute-history", disabled=True),  # Initially disabled
            Button("Copy", id="copy-history", disabled=True), # Initially disabled
            id="history-buttons"
        )
        self.selected_entry_index = None

    def on_mount(self) -> None:
        """Called when the history browser is mounted."""
        if not self.history_data:
            self.query_one("#history-container").mount(Static("No history available.", style="italic grey"))
            self.query_one("#close-history").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler for button presses."""
        button_id = event.button.id
        if button_id == "close-history":
            self.app.pop_screen()
        elif button_id == "execute-history":
             if self.selected_entry_index is not None:
                command = self.history_data[self.selected_entry_index]['command']
                self.app.exit(command)
        elif button_id == "copy-history":
            if self.selected_entry_index is not None:
                command = self.history_data[self.selected_entry_index]['command']
                self.app.exit(("copy", command))

    def on_click(self, event) -> None:
        """Handles clicks on history entries."""
        if str(event.target).startswith("Static(markup='[bold]Query:[/bold]"):
            # Deselect previous selection
            for entry in self.query_all("#history-entry"):
                entry.styles.background = "transparent"
                entry.styles.color = "bright_white"

            # Select new entry
            event.target.styles.background = "SteelBlue"
            event.target.styles.color = "black"
            # Extract the index from the target id
            history_entries = self.query_all("#history-entry").all()
            self.selected_entry_index = history_entries.index(event.target)

            # Enable buttons
            self.query_one("#execute-history").disabled = False
            self.query_one("#copy-history").disabled = False
            self.query_one("#execute-history").focus()


class ApiKeyApp(App[Union[str, None]]):
    """TUI App to prompt for the Gemini API Key."""
    TITLE = "1Q API Key Setup"
    SUB_TITLE = "Enter your Google AI Studio API Key"
    CSS_PATH = None # Inline CSS below

    CSS = """
    Screen { align: center middle; }
    Vertical { width: auto; height: auto; }
    Input { width: 60; }
    Button { margin-top: 1; width: 20; }
    Label { margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.SUB_TITLE),
            Input(password=True, placeholder="Paste API Key Here", id="api-key-input"),
            Horizontal(
                Button("Save", variant="primary", id="save-button"),
                Button("Cancel", variant="default", id="cancel-button"),
                ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler for button presses."""
        if event.button.id == "save-button":
            api_key = self.query_one("#api-key-input", Input).value.strip()
            if api_key:
                self.exit(api_key)
            else:
                self.notify("API Key cannot be empty.", title="Input Error", severity="error", timeout=2.0)
        elif event.button.id == "cancel-button":
            self.exit(None)


ResponseAppResult = Optional[Literal["execute", "modify", "refine", "copy", "history"]]

class ResponseApp(App[ResponseAppResult]):
    """TUI App to display the response and options."""

    TITLE = "1Q - Response"
    CSS_PATH = None

    CSS = """
    Screen {
        layout: vertical;
    }

    #response-container {
        layout: vertical;
        width: auto;
        height: auto;
        margin: 1;
        border: tall $primary 2;
        padding: 1;
    }
    
    #button-container {
        layout: horizontal;
        height: auto;
        margin: 1;
        align: center middle;
    }

    Markdown {
        width: auto;
    }
    """
    BINDINGS = [
        Binding("escape", "app.quit", "Quit", show=False),
        Binding("ctrl+e", "execute_command", "Execute", show=True),
        Binding("ctrl+c", "copy_command", "Copy", show=True),
        Binding("ctrl+m", "modify_command", "Modify", show=True),
        Binding("ctrl+r", "refine_query", "Refine", show=True),
        Binding("ctrl+h", "view_history", "History", show=True),

    ]

    def __init__(self, response_data: Dict[str, Any], name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None):
         super().__init__(name=name, id=id, classes=classes)
         self.response_data = response_data
         self.query_text = response_data.get("query", "No query provided.")
         self.command_text = response_data.get("command", "")
         self.explanation_text = response_data.get("explanation", "")

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(title=self.TITLE, tall=False)
        with Container(id="response-container"):
            yield Markdown(f"[bold]Query:[/bold]\n{self.query_text}\n\n[bold]Command:[/bold]\n{self.command_text}\n\n[bold]Explanation:[/bold]\n{self.explanation_text}")

        with Container(id="button-container"):
            yield Button("Execute", variant="primary", id="execute")
            yield Button("Copy", id="copy")
            yield Button("Modify", id="modify")
            yield Button("Refine", id="refine")
            yield Button("History", id="history")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.set_focus(self.query_one("#execute", Button))

    def on_button_pressed(self, event