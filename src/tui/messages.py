"""Textual Message subclasses for routing bridge events through the Textual message pump.

These messages are posted from the async bridge worker and handled by AgentBureauApp.
Handler naming convention (Textual auto-routes):
  TokenReceived    -> on_token_received
  AgentFinished    -> on_agent_finished
  ClassificationDone -> on_classification_done

Phase 4 messages (flow control and code apply):
  RoundBoundary      -> on_round_boundary
  DebateEnded        -> on_debate_ended
  ReconciliationReady -> on_reconciliation_ready
  ApplyResult        -> on_apply_result
"""
from __future__ import annotations

from dataclasses import dataclass

from textual.message import Message

from tui.event_bus import BridgeEvent


# --- Phase 3 messages ---

@dataclass
class TokenReceived(Message):
    """A single streamed token line from an agent subprocess."""

    agent: str
    text: str


@dataclass
class AgentFinished(Message):
    """An agent's terminal event (AgentDone, AgentError, or AgentTimeout)."""

    agent: str
    event: BridgeEvent


@dataclass
class ClassificationDone(Message):
    """Disagreement classification results, ready to display."""

    disagreements: list   # list[disagree_v1.models.Disagreement]
    full_texts: dict      # {agent_name: str}


# --- Phase 4 messages ---

@dataclass
class RoundBoundary(Message):
    """Signals the start of a new debate round; triggers divider line in both panes."""

    round_num: int


@dataclass
class DebateEnded(Message):
    """Signals that debate rounds are complete; triggers pick-winner transition."""


@dataclass
class ReconciliationReady(Message):
    """Reconciliation output ready for panel display."""

    discussion_text: str
    diff_text: str
    agreed_code: str
    language: str


@dataclass
class ApplyResult(Message):
    """User confirmed or rejected a code write operation."""

    confirmed: bool
    files_written: list[str]
