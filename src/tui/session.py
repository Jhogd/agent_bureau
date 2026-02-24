"""Session state machine for Agent Bureau.

SessionState drives all state-dependent UI: Input disabled state,
status bar text, and pane header highlights. Transitions:

  IDLE -> STREAMING   (on prompt submission)
  STREAMING -> CLASSIFYING  (on both AgentFinished received)
  CLASSIFYING -> DONE  (on ClassificationDone received)
  DONE -> FLOW_PICK  (on flow control entry)

Phase 4 transitions:
  DONE -> FLOW_PICK  (user decides pick-one or live-debate)
  FLOW_PICK -> DEBATING  (user chose live-debate)
  DEBATING -> PICK_WINNER  (debate rounds complete)
  PICK_WINNER -> RECONCILING  (user selected winning agent)
  RECONCILING -> CONFIRMING_APPLY  (reconciliation + diff ready)
  CONFIRMING_APPLY -> IDLE  (user confirmed or rejected write)
"""
from __future__ import annotations

from enum import Enum, auto


class SessionState(Enum):
    """State machine states for a live agent session."""

    # Phase 3 states — do not modify or reorder
    IDLE = auto()
    STREAMING = auto()
    CLASSIFYING = auto()
    DONE = auto()

    # Phase 4 additions — flow control and code apply
    FLOW_PICK = auto()         # waiting for user to select pick-one or live-debate
    DEBATING = auto()          # live-debate rounds in progress
    PICK_WINNER = auto()       # waiting for user to select which agent won
    RECONCILING = auto()       # agents producing reconciliation + diff
    CONFIRMING_APPLY = auto()  # showing diff, waiting for user y/n
