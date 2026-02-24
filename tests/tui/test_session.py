"""Failing tests for tui.session — RED phase.

Tests verify that SessionState is an Enum with exactly four states:
IDLE, STREAMING, CLASSIFYING, DONE.
"""
from tui.session import SessionState
from enum import Enum


def test_session_state_is_enum():
    # Assert
    assert issubclass(SessionState, Enum)


def test_session_state_has_four_values():
    # Assert
    assert len(list(SessionState)) == 4


def test_session_state_values_named():
    # Assert — all four named states are accessible
    assert SessionState.IDLE
    assert SessionState.STREAMING
    assert SessionState.CLASSIFYING
    assert SessionState.DONE


def test_idle_is_falsy_in_streaming_check():
    # Assert — IDLE is not in the "active" states (models Input.disabled condition)
    assert SessionState.IDLE not in (SessionState.STREAMING, SessionState.CLASSIFYING)
