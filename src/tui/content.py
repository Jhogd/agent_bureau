"""Content rendering utilities for AgentPane.

Parses markdown-like text and writes to a Textual RichLog:
- Fenced code blocks (```language ... ```) -> rich.syntax.Syntax objects
- Plain prose lines -> written as strings
- Inline code (`backticks`) -> written with [bold cyan] Rich markup
- Empty / whitespace-only lines -> skipped
"""
import re
from rich.syntax import Syntax

FENCE_OPEN = re.compile(r"^```(\w+)$")
FENCE_CLOSE = re.compile(r"^```$")
INLINE_CODE = re.compile(r"`([^`]+)`")

SCROLLBACK_LIMIT = 5000  # max_lines for RichLog — prevents OOM on long sessions


def write_content_to_pane(log, text: str) -> None:
    """Write text to a RichLog widget, rendering fenced code blocks as Syntax objects.

    Args:
        log: A RichLog widget instance (or compatible .write() interface).
        text: Multi-line string of agent output, optionally containing fenced code blocks.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = FENCE_OPEN.match(line)
        if m:
            language = m.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not FENCE_CLOSE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            # Advance past the closing fence (if present)
            if i < len(lines):
                i += 1
            code = "\n".join(code_lines)
            log.write(
                Syntax(
                    code,
                    language,
                    theme="monokai",
                    indent_guides=True,
                    background_color="default",
                )
            )
        else:
            if line.strip():
                # Replace inline backtick code with Rich markup
                formatted = INLINE_CODE.sub(r"[bold cyan]\1[/bold cyan]", line)
                log.write(formatted)
            i += 1
