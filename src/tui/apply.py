"""Code proposal extraction, unified diff generation, and atomic file write.

This module provides pure stdlib functions for the code-apply pipeline:
- Parse fenced code blocks from agent output text
- Generate unified diffs between two code strings
- Write file content atomically via temp file + rename

No side effects occur without explicit function calls.
"""
import difflib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

FENCE_OPEN = re.compile(r'^```(\w+)$')
FENCE_CLOSE = re.compile(r'^```$')
FILE_COMMENT = re.compile(r'^#\s+(\S+\.\w+)$|^//\s+(\S+\.\w+)$')


@dataclass
class CodeProposal:
    """A fenced code block extracted from agent output.

    Attributes:
        language: Programming language from the fence opening (e.g. "python").
        code: Code content without fences and without the filename comment line.
        filename: File path if the first code line matched FILE_COMMENT; None otherwise.
    """

    language: str
    code: str
    filename: str | None


def extract_code_proposals(full_text: str) -> list[CodeProposal]:
    """Extract all fenced code blocks from agent output text.

    Parses all blocks delimited by ```language ... ```. If the first line of a
    block matches FILE_COMMENT (# path/to/file or // path/to/file), stores it
    as CodeProposal.filename and excludes it from the code content.

    Args:
        full_text: Multi-line string of agent output, possibly containing fenced code blocks.

    Returns:
        List of CodeProposal instances; empty list if no fenced blocks found.
    """
    proposals = []
    lines = full_text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if m:
            language = m.group(1)
            code_lines = []
            i += 1
            filename = None
            while i < len(lines) and not FENCE_CLOSE.match(lines[i]):
                # Check only the first code line for a file path comment
                if not code_lines:
                    fm = FILE_COMMENT.match(lines[i])
                    if fm:
                        filename = fm.group(1) or fm.group(2)
                        i += 1
                        continue
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing fence
            proposals.append(
                CodeProposal(
                    language=language,
                    code='\n'.join(code_lines),
                    filename=filename,
                )
            )
        else:
            i += 1
    return proposals


def generate_unified_diff(
    a_code: str,
    b_code: str,
    fromfile: str = "agent_a",
    tofile: str = "agent_b",
) -> str:
    """Generate a unified diff between two code strings.

    Uses difflib.unified_diff() with keepends=True to avoid trailing newline
    pitfalls. Returns an empty string when both inputs are identical.

    Args:
        a_code: Original code string (agent A's version).
        b_code: New code string (agent B's version).
        fromfile: Label for the "from" file header in the diff (default "agent_a").
        tofile: Label for the "to" file header in the diff (default "agent_b").

    Returns:
        Unified diff string, or "" if inputs are identical.
    """
    a_lines = a_code.splitlines(keepends=True)
    b_lines = b_code.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile)
    )
    result = ''.join(diff_lines)
    return result if result.strip() else ""


def write_file_atomic(target: Path, content: str) -> None:
    """Write content to target path atomically via temp file + rename.

    Creates parent directories as needed. The temp file is created in the same
    directory as the target (not /tmp) so that os.rename() stays within one
    filesystem and remains atomic on POSIX. On any exception during write the
    temp file is unlinked before re-raising.

    Args:
        target: Destination Path to write.
        content: String content to write to the file.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, 'w') as f:
            f.write(content)
        os.rename(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
