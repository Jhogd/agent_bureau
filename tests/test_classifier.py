"""Tests for disagree_v1.classifier — text-based disagreement detection."""
import pytest

from disagree_v1.classifier import classify_disagreements
from disagree_v1.models import Disagreement


# ---------------------------------------------------------------------------
# No code blocks
# ---------------------------------------------------------------------------


def test_both_empty_returns_no_disagreements():
    # Arrange / Act
    result = classify_disagreements("", "")

    # Assert
    assert result == []


def test_plain_text_no_code_returns_no_disagreements():
    # Arrange / Act
    result = classify_disagreements("Here is my explanation.", "Here is a different explanation.")

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Missing code (one agent has code, other doesn't)
# ---------------------------------------------------------------------------


def test_one_agent_has_code_other_does_not():
    # Arrange
    text_a = "```python\nprint('hello')\n```"
    text_b = "I would use a print statement."

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert len(result) == 1
    assert result[0].kind == "missing_code"


def test_missing_code_reversed():
    # Arrange
    text_a = "I would use a print statement."
    text_b = "```python\nprint('hello')\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert any(d.kind == "missing_code" for d in result)


# ---------------------------------------------------------------------------
# Identical code — no disagreement
# ---------------------------------------------------------------------------


def test_identical_code_blocks_no_disagreements():
    # Arrange
    code = "```python\n# src/foo.py\ndef foo():\n    return 42\n```"

    # Act
    result = classify_disagreements(code, code)

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Language mismatch
# ---------------------------------------------------------------------------


def test_different_languages_detected():
    # Arrange
    text_a = "```python\nprint('hello')\n```"
    text_b = "```javascript\nconsole.log('hello');\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert any(d.kind == "language_mismatch" for d in result)


def test_language_mismatch_summary_names_both_languages():
    # Arrange
    text_a = "```python\nprint('hello')\n```"
    text_b = "```javascript\nconsole.log('hello');\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    mismatch = next(d for d in result if d.kind == "language_mismatch")
    assert "python" in mismatch.summary
    assert "javascript" in mismatch.summary


# ---------------------------------------------------------------------------
# Filename mismatch
# ---------------------------------------------------------------------------


def test_different_filenames_detected():
    # Arrange
    text_a = "```python\n# src/foo.py\ndef foo(): pass\n```"
    text_b = "```python\n# src/bar.py\ndef foo(): pass\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert any(d.kind == "filename_mismatch" for d in result)


def test_same_filename_no_filename_mismatch():
    # Arrange
    text_a = "```python\n# src/foo.py\ndef foo(): return 1\n```"
    text_b = "```python\n# src/foo.py\ndef foo(): return 2\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert not any(d.kind == "filename_mismatch" for d in result)


# ---------------------------------------------------------------------------
# Code content differs
# ---------------------------------------------------------------------------


def test_different_implementations_detected():
    # Arrange
    text_a = "```python\ndef foo():\n    return 1\n```"
    text_b = "```python\ndef foo():\n    return 2\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert any(d.kind == "code_differs" for d in result)


def test_identical_implementation_no_code_differs():
    # Arrange
    code = "```python\ndef foo():\n    return 42\n```"

    # Act
    result = classify_disagreements(code, code)

    # Assert
    assert not any(d.kind == "code_differs" for d in result)


# ---------------------------------------------------------------------------
# Multiple disagreements
# ---------------------------------------------------------------------------


def test_language_and_code_both_detected():
    # Arrange
    text_a = "```python\ndef foo(): return 1\n```"
    text_b = "```javascript\nfunction foo() { return 2; }\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    kinds = {d.kind for d in result}
    assert "language_mismatch" in kinds
    assert "code_differs" in kinds


# ---------------------------------------------------------------------------
# Multiple blocks — uses last block for comparison
# ---------------------------------------------------------------------------


def test_uses_last_block_when_multiple_present():
    # Arrange — first blocks differ, last blocks identical
    shared = "def final(): pass"
    text_a = "```python\ndef first(): return 1\n```\n```python\n" + shared + "\n```"
    text_b = "```python\ndef first(): return 2\n```\n```python\n" + shared + "\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert — last blocks match so no code_differs
    assert not any(d.kind == "code_differs" for d in result)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_returns_list_of_disagreement_instances():
    # Arrange
    text_a = "```python\nreturn 1\n```"
    text_b = "```python\nreturn 2\n```"

    # Act
    result = classify_disagreements(text_a, text_b)

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(d, Disagreement) for d in result)
