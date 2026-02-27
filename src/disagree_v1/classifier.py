"""Disagreement classifier for agent text responses.

Compares fenced code blocks between two agent outputs to classify
the nature of any disagreement. Works directly on raw text — no
JSON schema required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from disagree_v1.models import Disagreement

_FENCE_OPEN = re.compile(r'^```(\w+)$')
_FENCE_CLOSE = re.compile(r'^```$')
_FILE_COMMENT = re.compile(r'^#\s+(\S+\.\w+)$|^//\s+(\S+\.\w+)$')


@dataclass
class _Block:
    language: str
    content: str
    filename: str | None


def _extract_blocks(text: str) -> list[_Block]:
    """Extract fenced code blocks from agent output text."""
    blocks = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _FENCE_OPEN.match(lines[i])
        if m:
            language = m.group(1)
            content_lines: list[str] = []
            filename = None
            i += 1
            while i < len(lines) and not _FENCE_CLOSE.match(lines[i]):
                if not content_lines:
                    fm = _FILE_COMMENT.match(lines[i])
                    if fm:
                        filename = fm.group(1) or fm.group(2)
                        i += 1
                        continue
                content_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing fence
            blocks.append(_Block(
                language=language,
                content="\n".join(content_lines),
                filename=filename,
            ))
        else:
            i += 1
    return blocks


def classify_disagreements(text_a: str, text_b: str) -> list[Disagreement]:
    """Classify disagreements between two agent text responses.

    Compares fenced code blocks in both responses. Uses the last code block
    from each agent (the most likely final answer) for comparison.

    Args:
        text_a: Full text output from agent A.
        text_b: Full text output from agent B.

    Returns:
        List of Disagreement instances; empty if no meaningful differences found.
    """
    blocks_a = _extract_blocks(text_a)
    blocks_b = _extract_blocks(text_b)

    has_a = bool(blocks_a)
    has_b = bool(blocks_b)

    if not has_a and not has_b:
        return []

    if has_a != has_b:
        return [Disagreement(
            kind="missing_code",
            summary="One agent produced code blocks; the other did not.",
        )]

    # Both have code — compare the last (most relevant) block from each
    a = blocks_a[-1]
    b = blocks_b[-1]

    disagreements: list[Disagreement] = []

    if a.language != b.language:
        disagreements.append(Disagreement(
            kind="language_mismatch",
            summary=f"Agents used different languages: {a.language} vs {b.language}.",
        ))

    if a.filename != b.filename:
        disagreements.append(Disagreement(
            kind="filename_mismatch",
            summary=f"Agents targeted different files: {a.filename!r} vs {b.filename!r}.",
        ))

    if a.content.strip() != b.content.strip():
        disagreements.append(Disagreement(
            kind="code_differs",
            summary="Agents proposed different implementations.",
        ))

    return disagreements
