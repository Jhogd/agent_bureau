# Stack Research: Agent Bureau

**Research Date:** 2026-02-21
**Domain:** Python terminal TUI with multi-agent subprocess orchestration

---

## Recommended Stack

### TUI Framework: Textual

**Recommendation:** `textual>=0.70.0` (pin to `0.X.*` minor)

**Why Textual:**
- First-class `asyncio` integration — Textual's event loop is `asyncio`-native, which is essential for concurrent subprocess streaming without blocking the UI
- `RichLog` widget supports live append, scrollback limits, and Rich markup — ideal for streaming agent output
- `Horizontal` layout with dynamic column mounting covers the side-by-side pane requirement out of the box
- `ModalScreen` for per-session flow picker (pick vs. debate)
- `@work` decorator for running coroutines off the main thread with automatic message posting back to widgets
- Active maintenance (Textualize team); widely used for production CLI tools in 2025/2026
- Confidence: High

**What NOT to use:**
- `curses` — Too low-level; manual screen management adds weeks of work for no benefit
- `urwid` — Older, asyncio integration is bolted on, poor Rich/markup support
- `prompt_toolkit` — Great for REPL/input, not designed for multi-pane streaming layout
- `blessed` — No widget abstraction; raw terminal positioning only
- `Rich` alone — Rich is a rendering library, not a TUI framework; Textual is built on top of Rich

### Async Subprocess Streaming

**Recommendation:** `asyncio.create_subprocess_exec` (stdlib)

**Why:**
- Native asyncio; no thread pool needed for subprocess I/O
- `stdout=asyncio.subprocess.PIPE` with `await stream.readline()` or `await stream.read(n)` gives true streaming
- Pairs directly with Textual's `@work` coroutines
- Confidence: High

**Key pattern:**
```python
proc = await asyncio.create_subprocess_exec(
    *cmd_args,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    stdin=subprocess.DEVNULL,  # Critical: TUI owns stdin
)
async for line in proc.stdout:
    await queue.put(TokenChunk(agent_id=agent_id, text=line.decode()))
```

**PTY consideration:** Some CLI agents (claude, codex) detect non-TTY mode and suppress streaming or change output format. Use `pty.openpty()` (Unix) to give each subprocess a pseudo-terminal if buffering issues occur. Phase: streaming spike.

### ANSI Stripping

**Recommendation:** `strip_ansi` utility or `re.sub(r'\x1b\[[0-9;]*m', '', text)` inline

**Why:** CLI agents emit ANSI color codes that must be stripped before feeding to Textual's `RichLog` (which manages its own markup). Without stripping, escape codes render as literal characters or corrupt the pane.

### Packaging

**Recommendation:** `pyproject.toml` with `[project.scripts]` entry point

```toml
[project.scripts]
agent-bureau = "agent_bureau.tui.app:main"

[project.dependencies]
textual = ">=0.70.0,<1.0"
```

**Why:** Single `pip install .` + `agent-bureau` to launch. The `agent_bureau` package replaces `disagree_v1` as the top-level name. Textual `.tcss` style files must be included via `package_data` or `importlib.resources`.

### Testing

**Keep:** `pytest` (existing)

**Add:** `pytest-asyncio` for testing async bridge/streaming code

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "textual[dev]>=0.70.0"]
```

**Textual headless testing:** `textual[dev]` includes `App.run_test()` for automated TUI tests without a real terminal.

---

## Existing Stack (Keep As-Is)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Core orchestration | Python 3.10+ stdlib | `orchestrator.py` — no changes needed |
| Agent adapter protocol | Python Protocol (duck typing) | `adapters.py` — bridge bypasses for streaming |
| Disagreement classifier | stdlib | `classifier.py` — called post-stream |
| Adjudication prompts | stdlib | `adjudication.py` — no changes |
| Session persistence | JSONL (stdlib) | `store.py` — no changes |
| Build | setuptools + pyproject.toml | Extend, don't replace |

---

## Migration Path

1. Rename package `disagree_v1` → `agent_bureau` (or keep `disagree_v1` as internal subpackage)
2. Add `textual` and `pytest-asyncio` to `[project.dependencies]` and `[project.optional-dependencies.dev]`
3. New `src/agent_bureau/tui/` module — pure additions, no modification to existing core
4. Update `[project.scripts]` entry point

---

## Confidence Summary

| Decision | Confidence | Risk |
|----------|-----------|------|
| Textual as TUI framework | High | Version churn — pin minor version |
| asyncio subprocess streaming | High | PTY buffering — spike early |
| Keep existing core untouched | High | Low — bridge pattern isolates TUI |
| pytest-asyncio for tests | High | Low |

---

*Stack research: 2026-02-21*
