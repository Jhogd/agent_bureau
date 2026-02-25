"""StatusBar widget — one-line top bar showing session state and keyboard hints."""
from __future__ import annotations

from textual.widgets import Static

# Default text shown before the first prompt is submitted.
_INITIAL_TEXT = "Enter: submit  •  Ctrl-C: quit  •  Ctrl-L: clear"


class StatusBar(Static):
    """A one-line status bar at the top of the screen.

    Displays keyboard hints in IDLE state. Updated via update_status()
    when agent streaming state or classification results change.

    Uses Static.update() (inherited) for all text changes — no reactive
    needed; updates are driven by explicit calls from AgentBureauApp.
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel-darken-2;
        color: $text-muted;
        content-align: left middle;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(_INITIAL_TEXT, **kwargs)

    def show_hints(self) -> None:
        """Restore keyboard hint text (IDLE state)."""
        self.update(_INITIAL_TEXT)

    def show_streaming(self, agent_counts: dict[str, int]) -> None:
        """Update text while agents are streaming.

        Args:
            agent_counts: {agent_name: line_count} for all active agents.
        """
        parts = [f"{name}: streaming ({count} lines)" for name, count in agent_counts.items()]
        self.update("  •  ".join(parts))

    def show_done(self, agent_counts: dict[str, int]) -> None:
        """Update text when all agents have finished (before classification)."""
        parts = [f"{name}: {count} lines" for name, count in agent_counts.items()]
        self.update("Both done — " + ", ".join(parts))

    def show_classification(self, agent_counts: dict[str, int], disagreements: list) -> None:
        """Update text after classification completes.

        Args:
            agent_counts: {agent_name: line_count}
            disagreements: list[Disagreement] from classify_disagreements()
        """
        done_part = ", ".join(f"{name}: {count} lines" for name, count in agent_counts.items())
        if disagreements:
            kinds = ", ".join(d.kind for d in disagreements)
            classification_part = f"disagreement: {kinds}"
        else:
            classification_part = "agents agree"
        self.update(f"Both done — {done_part}  •  {classification_part}")

    def show_reconciling(self) -> None:
        """Update text during agent reconciliation."""
        self.update("Reconciling — each agent reviewing the other's proposal...")

    def show_reviewing(self, agent_counts: dict[str, int]) -> None:
        """Update text when reconciliation is done and review bar is active."""
        done_part = ", ".join(f"{name}: {count} lines" for name, count in agent_counts.items())
        self.update(f"Reconciled — {done_part}")

    def show_apply_confirm(self, file_count: int) -> None:
        """Update text during apply confirmation."""
        noun = "file" if file_count == 1 else "files"
        self.update(f"Ready to write {file_count} {noun}  •  y: apply  •  n: cancel")
