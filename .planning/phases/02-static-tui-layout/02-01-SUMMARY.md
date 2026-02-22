---
phase: 02-static-tui-layout
plan: "01"
subsystem: ui
tags: [textual, tui, pyproject, dependencies]

# Dependency graph
requires:
  - phase: 01-async-streaming-bridge
    provides: project scaffold with pyproject.toml and .venv
provides:
  - textual>=0.80.0,<9 pinned as runtime dependency in pyproject.toml
  - textual 8.0.0 installed and importable via project .venv
affects: [02-static-tui-layout, 03-live-streaming-integration, 04-agent-orchestration, 05-end-to-end]

# Tech tracking
tech-stack:
  added: [textual==8.0.0]
  patterns: [runtime dependency declared in pyproject.toml [project] dependencies]

key-files:
  created: []
  modified: [pyproject.toml]

key-decisions:
  - "Pin textual>=0.80.0,<9 (not >=0.70.0,<1.0) — textual is at major version 8.x; <1.0 upper bound would have failed to resolve"
  - "Use project .venv at /Users/jakeogden/agent-bureau/.venv — system pip is externally managed (PEP 668)"

patterns-established:
  - "Runtime dependencies declared in pyproject.toml [project] dependencies, dev-only in [project.optional-dependencies] dev"

requirements-completed: [TUI-06]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 2 Plan 01: Pin Textual Dependency Summary

**textual 8.0.0 pinned as runtime dependency in pyproject.toml with >=0.80.0,<9 constraint, installed and importable via project .venv**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T21:40:10Z
- **Completed:** 2026-02-22T21:42:10Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `"textual>=0.80.0,<9"` to `[project] dependencies` in pyproject.toml
- Installed textual 8.0.0 via `.venv/bin/pip install -e '.[dev]'`
- Verified `import textual` and `from textual.app import App; from textual.widgets import RichLog` succeed
- All 23 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin textual dependency in pyproject.toml** - `6944d91` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `pyproject.toml` - Added `"textual>=0.80.0,<9"` to `[project] dependencies`

## Decisions Made
- Corrected pin to `>=0.80.0,<9` per plan guidance; the roadmap decision log referenced `>=0.70.0,<1.0` which would have failed since textual is now at major version 8.x
- Used `.venv/bin/pip` instead of system `pip` because macOS system Python is externally managed (PEP 668)

## Deviations from Plan

None - plan executed exactly as written. The only implementation detail was discovering the project uses `.venv` at the project root (not system pip), which is standard Python practice and not a deviation.

## Issues Encountered
- System `pip` and `pip3` are blocked by macOS PEP 668 externally-managed-environment. Resolved by using the project's `.venv/bin/pip` which was already set up from Phase 1.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- textual 8.0.0 is installed and fully importable; all Phase 2 tasks can now `import textual` without additional setup
- All 23 Phase 1 tests continue to pass — no regressions
- Ready to proceed to 02-02 (first TUI widget implementation)

---
*Phase: 02-static-tui-layout*
*Completed: 2026-02-22*
