"""Textual Message subclasses for routing bridge events through the Textual message pump.

These messages are posted from the async bridge worker and handled by AgentBureauApp.
Handler naming convention (Textual auto-routes):
  TokenReceived    -> on_token_received
  AgentFinished    -> on_agent_finished
  ClassificationDone -> on_classification_done
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
    """An agent's terminal event (AgentDone, AgentError, or AgentTimeout)."""

    agent: str
    event: BridgeEvent


@dataclass
class ClassificationDone(Message):
    """Disagreement classification results, ready to display."""

    disagreements: list   # list[disagree_v1.models.Disagreement]
    full_texts: dict      # {agent_name: str}
