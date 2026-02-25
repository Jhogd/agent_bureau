"""ReviewBar — slim action bar shown after reconciliation completes."""
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class ReviewBar(Widget):
    """Slim one-line bar displayed during REVIEWING state.

    Hidden by default; appears below ReconciliationPanel when reconciliation
    finishes. Shows keyboard hints — the app handles the actual bindings.
    """

    DEFAULT_CSS = """
    ReviewBar {
        display: none;
        height: 1;
        background: $panel-darken-2;
        color: $text-muted;
        content-align: left middle;
        padding: 0 1;
    }
    """

    _HINT = "[r] Reconcile again  •  [c] Accept Claude  •  [x] Accept Codex  •  [y] Apply reconciled"

    def compose(self) -> ComposeResult:
        yield Static(self._HINT)

    def show(self) -> None:
        self.display = True

    def hide(self) -> None:
        self.display = False
