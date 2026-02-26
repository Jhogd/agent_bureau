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
        color: $text-muted;
        content-align: left middle;
        padding: 0 1;
    }
    ReconciliationPanel #recon-header.success {
        background: $success-darken-2;
        color: $text;
    }
    ReconciliationPanel #recon-header.failure {
        background: $error-darken-2;
        color: $text;
    }
    ReconciliationPanel #recon-log {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Reconciliation", id="recon-header")
        yield RichLog(id="recon-log", highlight=True, markup=True)

    def show_reconciliation(self, diff_text: str, code_found: bool = True) -> None:
        """Display unified diff between the two reconciliation proposals. Makes panel visible.

        Args:
            diff_text:  Unified diff string (may be empty if proposals are identical).
            code_found: False when neither agent produced a fenced code block.
        """
        self.display = True
        header = self.query_one("#recon-header", Label)
        log = self.query_one("#recon-log", RichLog)
        log.clear()

        if not code_found:
            header.update("Reconciliation — no code blocks detected  •  [r] to retry")
            header.set_class(True, "failure")
            header.set_class(False, "success")
            log.write(
                "[bold red]Neither agent produced a fenced code block.[/bold red]\n"
                "Press [bold][r][/bold] to reconcile again, or check that agents "
                "are formatting responses with ``` fences."
            )
            return

        header.update("Reconciliation — diff: Claude vs Codex")
        header.set_class(True, "success")
        header.set_class(False, "failure")
        if diff_text.strip():
            log.write(Syntax(diff_text, "diff", theme="monokai", background_color="default"))
        else:
            log.write("[dim]No code differences — both reconciliations are identical.[/dim]")

    def show_merge_output(self, text: str) -> None:
        """Replace panel content with the merged output text. Makes panel visible."""
        self.display = True
        log = self.query_one("#recon-log", RichLog)
        log.clear()
        if text.strip():
            log.write(text)
        else:
            log.write("[dim]No content in merged output.[/dim]")

    def hide_panel(self) -> None:
        """Hide the panel and clear content (call on session reset)."""
        self.display = False
        self.query_one("#recon-log", RichLog).clear()
