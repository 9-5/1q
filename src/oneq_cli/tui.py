# D:\1q\src\oneq_cli\tui.py
# Textual User Interface components for 1Q.

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label

class OneqApp(App):
    """Basic TUI app for 1Q."""

    async def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(title="1Q - The right one-liner is just one query away.")
        yield Label("This is a placeholder TUI.")
        yield Footer()