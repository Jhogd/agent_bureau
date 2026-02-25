# Coding Conventions

**Analysis Date:** 2026-02-21

## Naming Patterns

**Files:**
- Module names use snake_case: `orchestrator.py`, `adjudication.py`, `launcher.py`
- No special prefixes or suffixes for file types
- Each file represents a single logical component

**Functions:**
- Use snake_case for all function names: `classify_disagreements()`, `build_reconcile_prompt()`, `detect_available_agents()`
- Private functions (internal to a module) are prefixed with underscore: `_normalize()`, `_default_runner()`, `_build_args()`, `_parse_payload()`, `_validate_payload()`, `_collect()`, `_print_result()`
- Constructor methods in dataclasses are automatically named `__init__`

**Variables:**
- Use snake_case for variable names: `agent_a`, `agent_b`, `session_store`, `command_template`, `tmp_path`
- Private instance variables use leading underscore: `self._agent_a`, `self._agent_b`, `self._session_store`, `self._path`
- Loop variables and accumulators are descriptive: `lines`, `detected`, `disagreements`, `names`, `payload`, `required`
- Constants use UPPER_CASE: `CONFIDENCE_GAP_THRESHOLD`

**Types:**
- Use PEP 484 type hints: `str`, `int`, `float`, `list[str]`, `dict[str, object]`, `dict[str, str]`, `tuple[str, str]`
- Use `from __future__ import annotations` for forward references (present at top of every module)
- Use Protocol for structural typing: `class AgentAdapter(Protocol):`
- Use dataclasses for data structures: `@dataclass` and `@dataclass(frozen=True)` for immutable data

## Code Style

**Formatting:**
- No explicit formatter tool configured (ruff, black, etc.)
- Follows PEP 8 style implicitly through convention
- 4-space indentation (Python standard)
- Line length appears unconstrained in examined code (longest lines ~120 characters)

**Linting:**
- No explicit linting tool configured (flake8, ruff, etc.)
- Code follows implicit linting standards

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first when used)
2. Standard library imports: `import`, `from`
3. Third-party imports (none in this codebase currently)
4. Local imports from the package: `from disagree_v1.xxx import`

**Path Aliases:**
- Direct relative imports within package: `from disagree_v1.adapters import CommandJsonAdapter`
- No path aliases configured in `pyproject.toml`

**Example from `orchestrator.py`:**
```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from disagree_v1.adapters import AgentAdapter
from disagree_v1.classifier import classify_disagreements
from disagree_v1.models import SessionResult
from disagree_v1.store import JsonlSessionStore
```

## Error Handling

**Patterns:**
- Use `ValueError` for validation and logic errors: raised in `CommandJsonAdapter._parse_payload()`, `CommandJsonAdapter._validate_payload()`, `adjudication.build_debate_prompt()`, `adjudication.apply_action()`
- Chain exceptions with `from exc` to preserve context: `raise ValueError(f"...") from exc`
- Catch specific exceptions: `except subprocess.TimeoutExpired`, `except json.JSONDecodeError`, `except (TypeError, ValueError)`
- Wrap external command execution in try-except: `_default_runner()` catches `subprocess.TimeoutExpired` and converts to `ValueError`
- Raise `ValueError` with descriptive messages for invalid inputs: `"{self.name} returned non-JSON output"`, `"{self.name} JSON missing required keys"`

**Error handling in adapters:**
```python
def _default_runner(args: list[str]) -> str:
    try:
        completed = subprocess.run(args, check=True, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as exc:
        command = " ".join(args[:3])
        raise ValueError(f"Command timed out: {command} ...") from exc
    return completed.stdout.strip()
```

## Logging

**Framework:** No logging framework detected. Uses `print()` for output.

**Patterns:**
- `_print_result()` function in `cli.py` and `launcher.py` formats and prints results to stdout
- No structured logging or debug levels
- CLI output is human-readable format, not machine-readable

## Comments

**When to Comment:**
- Docstrings are used for classes and protocols: `"""Deterministic local adapter for CLI/demo mode."""`, `"""Runs an external command and expects JSON payload for AgentResponse."""`
- No inline comments in examined code; code is self-documenting
- Docstrings follow triple-quote convention

**JSDoc/TSDoc:**
- Not applicable (Python project, not TypeScript/JavaScript)

## Function Design

**Size:**
- Most functions are small and focused (typically 10-30 lines)
- Longest examined function is `collect_two_agents()` at ~50 lines - still single-responsibility (collecting agent configuration)
- Single responsibility maintained throughout: each function does one thing

**Parameters:**
- Functions accept 1-4 parameters typically
- Use keyword-only arguments where semantically useful: `run(prompt: str)`, `append(payload: dict[str, object])`
- Default parameters used for optional configuration: `runner: Callable[[list[str]], str] = _default_runner`, `input_fn: Callable[[str], str] = input`
- Type hints are mandatory for all parameters

**Return Values:**
- Explicit return types annotated: `-> SessionResult`, `-> list[Disagreement]`, `-> None`, `-> dict[str, object]`
- Return single objects or tuples: `return session`, `return disagreements`, `tuple[dict[str, str], dict[str, str]]`
- Early returns for error cases or simple conditions are used
- `None` explicitly returned where no value is needed

## Module Design

**Exports:**
- Classes and functions defined at module level are implicitly exported
- No explicit `__all__` definitions in examined code
- Internal/private functions use leading underscore to indicate privacy

**Barrel Files:**
- `__init__.py` is minimal: `"""Visible disagreement v1 package."""` only
- No re-exports or aggregation in `__init__.py`
- Each module contains its own primary exports

**Dataclasses as Primary Data Structure:**
- Used throughout for data transfer objects: `AgentResponse`, `Disagreement`, `SessionResult`
- Frozen dataclasses for immutable data: `@dataclass(frozen=True)` prevents modification after creation
- Methods defined on dataclasses: `SessionResult.to_dict()` converts frozen dataclass to mutable dict
- No inheritance used; composition is the pattern

**Protocol-Based Abstraction:**
- `AgentAdapter` is a Protocol (structural type) allowing duck-typing
- Implementing classes like `StubAgentAdapter` and `CommandJsonAdapter` must define `run(prompt: str) -> AgentResponse`
- Orchestrator accepts `AgentAdapter` protocol without knowing concrete type

---

*Convention analysis: 2026-02-21*
