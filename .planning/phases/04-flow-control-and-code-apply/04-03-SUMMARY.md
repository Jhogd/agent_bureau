---
phase: 04-flow-control-and-code-apply
plan: "03"
subsystem: ui
tags: [python, stdlib, re, difflib, pathlib, tempfile, dataclass, tdd]

# Dependency graph
requires:
  - phase: 04-flow-control-and-code-apply
    provides: Phase 4 session states and messages (04-01)

provides:
  - CodeProposal dataclass with language, code, and filename fields
  - extract_code_proposals() — parse all fenced code blocks from agent output text
  - generate_unified_diff() — unified diff via difflib with keepends=True
  - write_file_atomic() — atomic file write via temp+rename in same filesystem

affects:
  - 04-05-PLAN.md (apply wire-up in app)
  - 04-06-PLAN.md (integration / e2e)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic write via mkstemp in target.parent + os.rename (same filesystem, POSIX atomic)"
    - "FILE_COMMENT regex: first code line # path/to/file or // path/to/file sets CodeProposal.filename"
    - "keepends=True on splitlines() for difflib to avoid trailing-newline pitfall"

key-files:
  created:
    - src/tui/apply.py
    - tests/tui/test_apply.py
  modified: []

key-decisions:
  - "Atomic write uses tempfile.mkstemp(dir=target.parent) — NOT dir='/tmp' — to stay on same filesystem for POSIX rename atomicity"
  - "generate_unified_diff uses splitlines(keepends=True) to avoid trailing newline omission pitfall in unified diff output"
  - "FILE_COMMENT only inspects the first code line; later comment lines are treated as code content"
  - "REFACTOR step (docstrings) folded into GREEN commit — all module and function docstrings present in feat(04-03)"

patterns-established:
  - "Pure stdlib module with no side effects — all writes require explicit function calls"
  - "AAA test structure throughout test_apply.py — Arrange / Act / Assert"

requirements-completed: [APPLY-01, APPLY-02, APPLY-03]

# Metrics
duration: 15min
completed: 2026-02-24
---

# Phase 4 Plan 03: Apply Module Summary

**Pure stdlib code-extraction pipeline: fenced block parser, unified diff generator, and atomic file writer proven via TDD with 13 tests**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-24T23:00:00Z
- **Completed:** 2026-02-24T23:16:10Z
- **Tasks:** 3 (RED, GREEN, REFACTOR)
- **Files modified:** 2

## Accomplishments

- `CodeProposal` dataclass with `language`, `code`, and `filename` fields
- `extract_code_proposals()` handles single blocks, multiple blocks, `#` and `//` filename comments, and no-block input
- `generate_unified_diff()` returns empty string for identical inputs; uses `keepends=True` to avoid trailing-newline pitfall
- `write_file_atomic()` creates parent dirs, uses `mkstemp` in `target.parent` (same filesystem), cleans up temp file on exception
- 13 tests, all passing; full suite (107 tests) remains green

## Task Commits

Each TDD phase committed atomically:

1. **RED — add failing tests for apply module** - `ecd9eae` (test)
2. **GREEN — implement apply module** - `aa03373` (feat)

_Note: REFACTOR step (docstrings) was folded into the GREEN commit — all docstrings were already present in `feat(04-03)`._

## Files Created/Modified

- `src/tui/apply.py` — CodeProposal dataclass; extract_code_proposals, generate_unified_diff, write_file_atomic; full module and function docstrings
- `tests/tui/test_apply.py` — 13 TDD tests covering all behaviors and edge cases

## Decisions Made

- **Atomic write stays in target.parent**: `tempfile.mkstemp(dir=target.parent)` instead of default `/tmp` — POSIX `os.rename()` is only atomic within the same filesystem. Cross-device rename would silently fall back to a non-atomic copy+delete.
- **`keepends=True` for diff**: `a_code.splitlines(keepends=True)` ensures line endings are preserved in the unified diff; without this, the last line of a block that lacks a trailing `\n` would be omitted from diff output.
- **FILE_COMMENT on first line only**: Only the first code line is tested against the filename comment pattern. Subsequent `#` comment lines are valid Python/JS code and must not be silently stripped.
- **REFACTOR folded into GREEN**: The plan called for a separate refactor commit to add docstrings. The GREEN implementation already included complete module and function docstrings, so no separate refactor commit was needed. No logic was changed.

## Deviations from Plan

None — plan executed as written. The REFACTOR step required no code changes because docstrings were included in the initial implementation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `src/tui/apply.py` is fully proven and ready for wiring into `app.py` in plans 04-05 and 04-06
- The `extract_code_proposals | write_file_atomic` import pattern specified in the plan's `key_links` is ready to consume
- No blockers; full test suite green

---
*Phase: 04-flow-control-and-code-apply*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: src/tui/apply.py
- FOUND: tests/tui/test_apply.py
- FOUND: .planning/phases/04-flow-control-and-code-apply/04-03-SUMMARY.md
- FOUND: commit ecd9eae (test(04-03): add failing tests for apply module)
- FOUND: commit aa03373 (feat(04-03): implement apply module with extract, diff, and atomic write)
- 13 tests passed (pytest tests/tui/test_apply.py -v)
- 107 tests passed (full suite, no regressions)
