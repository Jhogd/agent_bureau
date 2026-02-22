# Plan 01-03 Summary: PTY Agent Spike

**Completed:** 2026-02-22
**Status:** Script created, syntax valid, runs cleanly

## Claude Binary Availability

`claude` binary was found at `/opt/homebrew/bin/claude`.

## Observed PTY Mode Behavior

The spike was run from inside an active Claude Code session. The claude CLI detected the nested session and exited immediately with exit code 1, printing:

```
Error: Claude Code cannot be launched inside another Claude Code session.
Nested sessions share runtime resources and will crash all active sessions.
To bypass this check, unset the CLAUDECODE environment variable.
```

- PTY mode: **3 chunks** in 0.11s, first chunk at **+0.058s**
- Exit code: 1 (expected — nested session detection, not a streaming failure)

## Observed PIPE Mode Behavior

Same behavior — the error message was streamed identically in PIPE mode.

- PIPE mode: **3 chunks** in 0.06s, first chunk at **+0.058s**
- Exit code: 1

## Conclusion: PTY Required for claude?

**Unknown — needs confirmation outside nested session context.**

The spike could not test actual streaming because the claude binary refuses to run inside another Claude Code session. However, the spike revealed:

1. **Both PTY and PIPE streamed the error output** — both modes produced 3 chunks at ~0.058s first-chunk latency. This means the error path is not buffered in either mode.
2. **Buffering test inconclusive** — the real test (whether claude buffers stdout in PIPE mode when generating a real response) could not be run.
3. **PTY itself works** — `pty.openpty()` is available on this macOS system, O_NONBLOCK was set correctly, and the PTY reader loop functioned without error.
4. **Fallback warning path verified** — the spike's simulated PTY failure path correctly emits a `RuntimeWarning` with the expected message.

## Recommendation for Phase 3

**USE_PTY = True (safe default)** — confirmed PTY is available on this macOS system, and PTY is the correct choice for interactive CLI tools that detect terminal presence to enable streaming. When Agent Bureau is run outside Claude Code (normal use), the claude binary should stream correctly via PTY.

Document the `CLAUDECODE` environment variable: Phase 3 integration testing should unset it (or use a different terminal) when testing the real bridge with live claude invocations.

## Unexpected Behavior

- The claude CLI actively detects nested Claude Code sessions via the `CLAUDECODE` environment variable. This will affect integration testing in Phase 3 — tests that invoke the real claude binary must run outside the Claude Code environment.
- The spike verified that the PTY fallback RuntimeWarning path works correctly — the warning is emitted and the PIPE fallback activates cleanly.
