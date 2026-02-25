"""Session state machine for AgentBureauApp.

Transitions:
  IDLE -> STREAMING          (on prompt submission)
  STREAMING -> CLASSIFYING   (on both AgentFinished received)
  CLASSIFYING -> RECONCILING (on ClassificationDone — auto-starts reconciliation)
  RECONCILING -> REVIEWING   (on ReconciliationReady)
  REVIEWING -> RECONCILING   (user presses r — reconcile again)
  REVIEWING -> CONFIRMING_APPLY  (user accepts an answer)
  CONFIRMING_APPLY -> IDLE   (on ApplyResult)
"""
from __future__ import annotations

from enum import Enum, auto


class SessionState(Enum):
    """State machine states for a live agent session."""

    IDLE = auto()
    STREAMING = auto()
    CLASSIFYING = auto()
    RECONCILING = auto()       # auto-started after classification
    REVIEWING = auto()         # reconciliation done; user chooses next action
    CONFIRMING_APPLY = auto()  # diff shown, waiting for user y/n
