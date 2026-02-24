"""ReconciliationPanel widget — below-panes panel for agent reconciliation output.

Hidden by default (display=False). Becomes visible when show_reconciliation()
is called with the agent discussion text and unified diff.
"""
from __future__ import annotations

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, RichLog


class ReconciliationPanel(Widget):
    """Below-panes panel showing agent reconciliation discussion and unified diff.

    Hidden (display=False) until show_reconciliation() is called.
    Composes a header Label and a RichLog for discussion + syntax-highlighted diff.
    """

    DEFAULT_CSS = """
    ReconciliationPanel {
        height: 15;
        border-top: solid $border;
        display: none;
    }
    ReconciliationPanel #recon-header {
        height: 1;
        background: $panel-darken-1;
        content-align: left middle;
        padding: 0 1;
    }
    ReconciliationPanel #recon-log {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Reconciliation", id="recon-header")
        yield RichLog(id="recon-log", highlight=True, markup=True)

    def show_reconciliation(self, discussion: str, diff_text: str) -> None:
        """Display reconciliation discussion and unified diff. Makes panel visible.

        Args:
            discussion: Plain-text discussion from the reconciliation agent.
            diff_text: Unified diff string (may be empty if proposals are identical).
        """
        self.display = True
        log = self.query_one("#recon-log", RichLog)
        log.clear()
        if discussion:
            log.write(discussion)
        if diff_text.strip():
            log.write(Syntax(diff_text, "diff", theme="monokai", background_color="default"))
        else:
            log.write("[dim]No code differences detected — proposals are identical.[/dim]")

    def hide_panel(self) -> None:
        """Hide the panel and clear content (call on session reset)."""
        self.display = False
        self.query_one("#recon-log", RichLog).clear()
