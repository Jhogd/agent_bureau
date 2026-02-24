"""Tests for tui.session — Phase 3 and Phase 4 states.

Tests verify that SessionState is an Enum with all 9 states:
IDLE, STREAMING, CLASSIFYING, DONE (Phase 3)
FLOW_PICK, DEBATING, PICK_WINNER, RECONCILING, CONFIRMING_APPLY (Phase 4)
"""
from tui.session import SessionState
from enum import Enum


def test_session_state_is_enum():
    # Assert
    assert issubclass(SessionState, Enum)


def test_session_state_has_nine_values():
    # Assert — all 9 states: 4 Phase 3 + 5 Phase 4
    assert len(list(SessionState)) == 9


def test_session_state_phase3_values_named():
    # Assert — all four Phase 3 named states are accessible
    assert SessionState.IDLE
    assert SessionState.STREAMING
    assert SessionState.CLASSIFYING
    assert SessionState.DONE


def test_session_state_phase4_values_named():
    # Assert — all five Phase 4 named states are accessible
    assert SessionState.FLOW_PICK
    assert SessionState.DEBATING
    assert SessionState.PICK_WINNER
    assert SessionState.RECONCILING
    assert SessionState.CONFIRMING_APPLY


def test_session_state_members_are_distinct():
    # Assert — auto() assigns unique integer values; no duplicates
    values = [s.value for s in SessionState]
    assert len(values) == len(set(values))


def test_idle_is_not_flow_pick():
    # Assert — IDLE.value != FLOW_PICK.value (auto() assigns unique ints)
    assert SessionState.IDLE.value != SessionState.FLOW_PICK.value


def test_idle_is_falsy_in_streaming_check():
    # Assert — IDLE is not in the "active" states (models Input.disabled condition)
    assert SessionState.IDLE not in (SessionState.STREAMING, SessionState.CLASSIFYING)


def test_phase4_states_in_session_state():
    # Assert — Phase 4 states are members of the enum
    assert SessionState.FLOW_PICK in SessionState
    assert SessionState.DEBATING in SessionState
    assert SessionState.PICK_WINNER in SessionState
    assert SessionState.RECONCILING in SessionState
    assert SessionState.CONFIRMING_APPLY in SessionState
