"""ApplyConfirmScreen — y/n confirmation gate before writing files to disk.

Dismiss contract: dismisses with True (write files) or False (reject/cancel).
No file is written without an explicit 'y' from this screen.
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class ApplyConfirmScreen(ModalScreen[bool]):
    """Confirmation dialog before applying proposed code changes.

    Shows the target filename and a short code preview so the user knows
    exactly what will be written before pressing y.

    Returns True if user presses 'y' (write files), False on 'n' or Escape.
    """

    DEFAULT_CSS = """
    ApplyConfirmScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #apply-dialog {
        width: 80;
        height: auto;
        max-height: 24;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    #apply-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #apply-filename {
        color: $text;
        margin-bottom: 1;
    }
    #apply-preview {
        height: auto;
        max-height: 12;
        color: $text-muted;
        border: solid $panel;
        padding: 0 1;
        overflow-y: auto;
        margin-bottom: 1;
    }
    #apply-hint {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Write files"),
        Binding("n", "reject", "Cancel"),
        Binding("escape", "reject", "Cancel"),
    ]

    def __init__(self, filename: str | None = None, code: str = "") -> None:
        super().__init__()
        self._filename = filename
        self._code = code

    def compose(self) -> ComposeResult:
        with Vertical(id="apply-dialog"):
            yield Label("Apply changes to disk?", id="apply-title")

            if self._filename:
                yield Label(f"File: {self._filename}", id="apply-filename")
            else:
                yield Label("File: (no filename detected — will not write)", id="apply-filename")

            if self._code.strip():
                # Show first 20 lines of code as plain text (no markup interpretation)
                preview_lines = self._code.splitlines()[:20]
                if len(self._code.splitlines()) > 20:
                    preview_lines.append("...")
                preview = Text("\n".join(preview_lines))
                yield Static(preview, id="apply-preview")

            hint = "[y] Write file   [n] Cancel" if self._filename else "[n] Cancel  (set a filename comment in the code block to enable writing)"
            yield Label(hint, id="apply-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
