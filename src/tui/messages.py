"""Textual message types for AgentBureauApp inter-component communication.

Handler naming convention (Textual auto-routes):
  TokenReceived       -> on_token_received
  AgentFinished       -> on_agent_finished
  ClassificationDone  -> on_classification_done
  ReconciliationReady -> on_reconciliation_ready
  ApplyResult         -> on_apply_result
"""
from __future__ import annotations

from dataclasses import dataclass

from textual.message import Message

from tui.event_bus import BridgeEvent


@dataclass
class TokenReceived(Message):
    """A single streamed token line from an agent subprocess."""

    agent: str
    text: str


@dataclass
class AgentFinished(Message):
    """A terminal bridge event (done/error/timeout) from one agent."""

    agent: str
    event: BridgeEvent


@dataclass
class ClassificationDone(Message):
    """Disagreement classification complete."""

    disagreements: list   # list[disagree_v1.models.Disagreement]
    full_texts: dict      # {agent_name: str}


@dataclass
class ReconciliationReady(Message):
    """Both agents finished their reconciliation passes; diff is ready for display."""

    diff_text: str


@dataclass
class ApplyResult(Message):
    """User confirmed or rejected a code write operation."""

    confirmed: bool
    files_written: list[str]
