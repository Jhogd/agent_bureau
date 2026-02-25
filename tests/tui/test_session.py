"""Tests for tui.session — 6-state machine.

States: IDLE, STREAMING, CLASSIFYING, RECONCILING, REVIEWING, CONFIRMING_APPLY
"""
from tui.session import SessionState
from enum import Enum


def test_session_state_is_enum():
    # Assert
    assert issubclass(SessionState, Enum)


def test_session_state_has_six_values():
    # Assert — exactly 6 states
    assert len(list(SessionState)) == 6


def test_session_state_values_named():
    # Assert — all six named states are accessible
    assert SessionState.IDLE
    assert SessionState.STREAMING
    assert SessionState.CLASSIFYING
    assert SessionState.RECONCILING
    assert SessionState.REVIEWING
    assert SessionState.CONFIRMING_APPLY


def test_session_state_members_are_distinct():
    # Assert — auto() assigns unique integer values; no duplicates
    values = [s.value for s in SessionState]
    assert len(values) == len(set(values))


def test_idle_is_not_streaming():
    # Assert — IDLE.value != STREAMING.value
    assert SessionState.IDLE.value != SessionState.STREAMING.value


def test_idle_is_falsy_in_streaming_check():
    # Assert — IDLE is not in the "active" states (models Input.disabled condition)
    assert SessionState.IDLE not in (SessionState.STREAMING, SessionState.CLASSIFYING)


def test_all_states_in_session_state():
    # Assert — all states are members of the enum
    assert SessionState.IDLE in SessionState
    assert SessionState.STREAMING in SessionState
    assert SessionState.CLASSIFYING in SessionState
    assert SessionState.RECONCILING in SessionState
    assert SessionState.REVIEWING in SessionState
    assert SessionState.CONFIRMING_APPLY in SessionState
