"""WinnerPickerScreen — slim bottom bar for picking the debate winner.

Appears anchored to the bottom of the screen with a transparent background
so agent pane content remains fully visible above it.

Dismiss contract: dismisses with one of 'agent-a', 'agent-b',
'keep-discussing', or 'cancel' (str).
Escape dismisses with 'cancel'.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets._option_list import Option


class WinnerPickerScreen(ModalScreen[str]):
    """Slim bottom-bar pick-winner — pane content stays visible above it.

    Returns one of 'agent-a', 'agent-b', 'keep-discussing', or 'cancel' on dismiss.
    Escape cancels (no changes).
    """

    DEFAULT_CSS = """
    WinnerPickerScreen {
        align: left bottom;
        background: rgba(0, 0, 0, 0);
    }
    #winner-bar {
        width: 100%;
        height: auto;
        background: $panel-darken-2;
        padding: 0 1;
    }
    #winner-hint {
        width: 100%;
        height: 1;
        color: $text-muted;
        content-align: left middle;
    }
    #winner-options {
        width: 100%;
        height: auto;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "action_cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="winner-bar"):
            yield Label("↑↓ pick winner  •  Enter confirm  •  Esc cancel", id="winner-hint")
            yield OptionList(
                Option("Claude wins", id="agent-a"),
                Option("Codex wins", id="agent-b"),
                Option("Keep discussing", id="keep-discussing"),
                Option("Cancel (no changes)", id="cancel"),
                id="winner-options",
                compact=True,
            )

    def on_mount(self) -> None:
        self.query_one("#winner-options", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)

    def action_cancel(self) -> None:
        self.dismiss("cancel")
