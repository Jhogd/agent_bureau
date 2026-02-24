"""Tests for apply.py — code extraction, diff generation, and atomic file write."""
import pytest
from pathlib import Path

from tui.apply import CodeProposal, extract_code_proposals, generate_unified_diff, write_file_atomic


# ---------------------------------------------------------------------------
# extract_code_proposals
# ---------------------------------------------------------------------------


def test_extract_single_fenced_block():
    # Arrange
    text = "```python\nprint('hello')\n```"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert len(proposals) == 1
    assert proposals[0].language == "python"
    assert proposals[0].code == "print('hello')"
    assert proposals[0].filename is None


def test_extract_block_with_filename_comment_hash():
    # Arrange
    text = "```python\n# src/foo.py\nprint('hello')\n```"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert len(proposals) == 1
    assert proposals[0].filename == "src/foo.py"
    assert proposals[0].code == "print('hello')"


def test_extract_block_with_filename_comment_slash():
    # Arrange
    text = "```javascript\n// src/foo.js\nconsole.log('hello');\n```"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert len(proposals) == 1
    assert proposals[0].filename == "src/foo.js"
    assert proposals[0].code == "console.log('hello');"


def test_extract_multiple_blocks():
    # Arrange
    text = "```python\ncode1\n```\n\n```javascript\ncode2\n```"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert len(proposals) == 2
    assert proposals[0].language == "python"
    assert proposals[0].code == "code1"
    assert proposals[1].language == "javascript"
    assert proposals[1].code == "code2"


def test_extract_no_blocks():
    # Arrange
    text = "no fences here, just plain text"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert proposals == []


def test_extract_code_without_filename_is_none():
    # Arrange
    text = "```python\nprint('hello')\n```"

    # Act
    proposals = extract_code_proposals(text)

    # Assert
    assert proposals[0].filename is None


# ---------------------------------------------------------------------------
# generate_unified_diff
# ---------------------------------------------------------------------------


def test_generate_diff_identical():
    # Arrange
    code = "def foo():\n    return 42\n"

    # Act
    diff = generate_unified_diff(code, code)

    # Assert
    assert diff == ""


def test_generate_diff_different():
    # Arrange
    a_code = "a\n"
    b_code = "b\n"

    # Act
    diff = generate_unified_diff(a_code, b_code)

    # Assert
    assert "--- agent_a" in diff
    assert "+++ agent_b" in diff


def test_generate_diff_custom_fromfile():
    # Arrange
    a_code = "old line\n"
    b_code = "new line\n"

    # Act
    diff = generate_unified_diff(a_code, b_code, fromfile="agent_claude")

    # Assert
    assert "--- agent_claude" in diff


# ---------------------------------------------------------------------------
# write_file_atomic
# ---------------------------------------------------------------------------


def test_write_file_atomic_creates_file(tmp_path):
    # Arrange
    target = tmp_path / "output.txt"
    content = "hello world"

    # Act
    write_file_atomic(target, content)

    # Assert
    assert target.exists()


def test_write_file_atomic_creates_parents(tmp_path):
    # Arrange
    target = tmp_path / "sub" / "file.py"
    content = "print('hello')"

    # Act
    write_file_atomic(target, content)

    # Assert
    assert target.parent.exists()
    assert target.exists()


def test_write_file_atomic_content_correct(tmp_path):
    # Arrange
    target = tmp_path / "output.py"
    content = "def foo():\n    return 42\n"

    # Act
    write_file_atomic(target, content)

    # Assert
    assert target.read_text() == content


def test_write_file_atomic_overwrites(tmp_path):
    # Arrange
    target = tmp_path / "output.txt"
    write_file_atomic(target, "first content")

    # Act
    write_file_atomic(target, "second content")

    # Assert
    assert target.read_text() == "second content"
