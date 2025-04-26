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
    """TUI App to prompt for the Gemini API K
... (FILE CONTENT TRUNCATED) ...
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

    def action_copy_command(self) -> None:
        """Copies the command to the clipboard."""
        if cli.PYPERCLIP_AVAILABLE:
            try:
                import pyperclip
                pyperclip.copy(self.command_text)
                self.notify("Command copied to clipboard!", title="Copied", severity="success", timeout=3.0)
            except pyperclip.PyperclipException:
                self.notify("Clipboard access failed. Ensure you have xclip or xsel installed.", title="Copy Failed", severity="error", timeout=5.0)
        else:
            self.notify("pyperclip not installed. Please install it to use clipboard functionality.", title="Copy Failed", severity="error", timeout=5.0)

def display_response_tui(response_data: Dict[str, Any]) -> ResponseAppResult:
    """Runs the ResponseApp and returns the chosen action."""
    app = ResponseApp(response_data=response_data) # Filtering happens in __init__
    result = app.run()
    return result