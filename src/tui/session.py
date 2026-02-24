"""Session state machine for Agent Bureau.

SessionState drives all state-dependent UI: Input disabled state,
status bar text, and pane header highlights. Transitions:

  IDLE -> STREAMING   (on prompt submission)
  STREAMING -> CLASSIFYING  (on both AgentFinished received)
  CLASSIFYING -> DONE  (on ClassificationDone received)
  DONE -> IDLE  (on next prompt submission, or auto after classification)
"""
from __future__ import annotations

from enum import Enum, auto


class SessionState(Enum):
    """State machine states for a live agent session."""

    IDLE = auto()
    STREAMING = auto()
    CLASSIFYING = auto()
    DONE = auto()
