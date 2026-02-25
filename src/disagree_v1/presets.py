from __future__ import annotations

import json


def _inline_schema() -> str:
    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "proposed_actions": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["answer", "proposed_actions", "assumptions", "confidence"],
        "additionalProperties": False,
    }
    return json.dumps(schema, separators=(",", ":"))


def build_claude_codex_commands(schema_path: str) -> tuple[str, str]:
    claude_schema = _inline_schema()
    claude_cmd = (
        "claude -p --output-format json "
        f"--json-schema '{claude_schema}' {{prompt}}"
    )
    codex_cmd = f"codex exec --skip-git-repo-check --output-schema {schema_path} {{prompt}}"
    return claude_cmd, codex_cmd
