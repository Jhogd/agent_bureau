"""Tests for tui.messages — message types.

Tests verify that TokenReceived, AgentFinished, ClassificationDone,
ReconciliationReady, and ApplyResult are Textual Message subclasses
with the correct typed fields.
"""
from tui.messages import (
    TokenReceived,
    AgentFinished,
    ClassificationDone,
    ReconciliationReady,
    ApplyResult,
)
from tui.event_bus import AgentDone, AgentError, AgentTimeout
from textual.message import Message


def test_token_received_is_message():
    # Arrange / Act
    msg = TokenReceived(agent="claude", text="hello")
    # Assert
    assert isinstance(msg, Message)


def test_token_received_fields():
    # Arrange
    agent = "claude"
    text = "foo"
    # Act
    msg = TokenReceived(agent=agent, text=text)
    # Assert
    assert msg.agent == "claude"
    assert msg.text == "foo"


def test_agent_finished_is_message():
    # Arrange / Act
    event = AgentDone(agent="codex", full_text="x", exit_code=0)
    msg = AgentFinished(agent="codex", event=event)
    # Assert
    assert isinstance(msg, Message)


def test_agent_finished_fields():
    # Arrange
    event = AgentDone(agent="codex", full_text="x", exit_code=0)
    # Act
    msg = AgentFinished(agent="codex", event=event)
    # Assert
    assert msg.agent == "codex"
    assert msg.event.type == "done"


def test_classification_done_is_message():
    # Arrange / Act
    msg = ClassificationDone(
        disagreements=[],
        full_texts={"claude": "x", "codex": "y"},
    )
    # Assert
    assert isinstance(msg, Message)


def test_classification_done_fields():
    # Arrange
    disagreements = []
    full_texts = {"claude": "x", "codex": "y"}
    # Act
    msg = ClassificationDone(disagreements=disagreements, full_texts=full_texts)
    # Assert
    assert msg.disagreements == []
    assert msg.full_texts == {"claude": "x", "codex": "y"}


def test_reconciliation_ready_fields():
    # Arrange / Act
    msg = ReconciliationReady(diff_text="--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new")
    # Assert
    assert msg.diff_text == "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new"


def test_reconciliation_ready_is_message():
    # Arrange / Act
    msg = ReconciliationReady(diff_text="")
    # Assert
    assert isinstance(msg, Message)


def test_apply_result_confirmed():
    # Arrange / Act
    msg = ApplyResult(confirmed=True, files_written=[])
    # Assert
    assert msg.confirmed is True


def test_apply_result_files_written():
    # Arrange / Act
    msg = ApplyResult(confirmed=False, files_written=["a.py"])
    # Assert
    assert msg.files_written == ["a.py"]


def test_apply_result_is_message():
    # Arrange / Act
    msg = ApplyResult(confirmed=True, files_written=["src/foo.py"])
    # Assert
    assert isinstance(msg, Message)
