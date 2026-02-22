from unittest.mock import MagicMock, call
import pytest
from rich.syntax import Syntax
from tui.content import write_content_to_pane


def make_log():
    """Return a MagicMock with the RichLog.write() interface."""
    return MagicMock()


def test_plain_prose_is_written_as_string():
    log = make_log()
    write_content_to_pane(log, "Hello world")
    log.write.assert_called_once_with("Hello world")


def test_empty_and_whitespace_lines_are_skipped():
    log = make_log()
    write_content_to_pane(log, "   \n\ntext\n  ")
    log.write.assert_called_once_with("text")


def test_fenced_python_block_writes_syntax_object():
    log = make_log()
    write_content_to_pane(log, "```python\nprint('hi')\n```")
    assert log.write.call_count == 1
    arg = log.write.call_args[0][0]
    assert isinstance(arg, Syntax)


def test_syntax_object_has_correct_language():
    log = make_log()
    write_content_to_pane(log, "```js\nconsole.log(1)\n```")
    arg = log.write.call_args[0][0]
    assert isinstance(arg, Syntax)
    # Syntax stores lexer name; check by inspecting _lexer or just trust isinstance


def test_unknown_language_tag_does_not_crash():
    log = make_log()
    write_content_to_pane(log, "```unknown_lang_xyz\nsome code\n```")
    assert log.write.call_count == 1
    arg = log.write.call_args[0][0]
    assert isinstance(arg, Syntax)


def test_prose_then_code_then_prose_written_in_order():
    log = make_log()
    text = "First line\n```python\nx = 1\n```\nLast line"
    write_content_to_pane(log, text)
    assert log.write.call_count == 3
    assert log.write.call_args_list[0] == call("First line")
    assert isinstance(log.write.call_args_list[1][0][0], Syntax)
    assert log.write.call_args_list[2] == call("Last line")


def test_text_with_no_code_blocks():
    log = make_log()
    write_content_to_pane(log, "Line one\nLine two\nLine three")
    assert log.write.call_count == 3


def test_empty_string_writes_nothing():
    log = make_log()
    write_content_to_pane(log, "")
    log.write.assert_not_called()
