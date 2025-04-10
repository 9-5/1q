# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

import sys
import re
from typing import Optional, Union, Dict, Any, Literal

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
    CSS_PATH = None # Inline CSS 
... (FILE CONTENT TRUNCATED) ...
        if event.button.id == "copy_button":
            self.exit("copy")

        elif event.button.id == "execute_button":
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