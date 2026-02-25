# Testing Patterns

**Analysis Date:** 2026-02-21

## Test Framework

**Runner:**
- pytest 8.0+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- Python path configured: `pythonpath = ["src"]`
- Quiet output: `addopts = "-q"`

**Assertion Library:**
- unittest.TestCase built-in assertions: `assertEqual()`, `assertIn()`, `assertGreaterEqual()`, `assertIsNone()`, `assertRaises()`
- No third-party assertion library (using standard unittest)

**Run Commands:**
```bash
pytest                                    # Run all tests
pytest tests/test_v1_flow.py             # Run specific test file
pytest -v                                 # Verbose output
pytest --tb=short                        # Shorter tracebacks
```

## Test File Organization

**Location:**
- Tests are in a separate `tests/` directory (not co-located with source)
- Single test file: `tests/test_v1_flow.py`
- Follows pytest convention of `test_*.py` naming

**Naming:**
- Test file: `test_v1_flow.py`
- Test class: `V1FlowTests(unittest.TestCase)` - descriptive name with "Tests" suffix
- Test methods: start with `test_` prefix
- Test method names are descriptive: `test_classifier_labels_approach_and_confidence_gap`, `test_orchestrator_runs_and_persists_session`, `test_store_appends_multiple_sessions`, `test_command_json_adapter_parses_structured_output`

**Structure:**
```
tests/
└── test_v1_flow.py          # Single test module for entire flow
```

## Test Structure

**Suite Organization:**
```python
class V1FlowTests(unittest.TestCase):
    def test_classifier_labels_approach_and_confidence_gap(self) -> None:
        # Arrange
        a = AgentResponse(...)
        b = AgentResponse(...)

        # Act
        disagreements = classify_disagreements(a, b)
        kinds = {d.kind for d in disagreements}

        # Assert
        self.assertIn("approach", kinds)
        self.assertIn("fact", kinds)
        self.assertIn("confidence_gap", kinds)
```

**Patterns:**
- **Arrange-Act-Assert (AAA):** Every test follows strict AAA structure
  - Arrange: Set up test data and fixtures
  - Act: Call the code being tested
  - Assert: Verify the results
- **No setup/teardown methods:** Each test is self-contained with its own arrangement
- **Explicit test data:** No shared fixtures; each test creates its own data
- **Comments separating phases:** No explicit comments in examined code, but structure makes phases clear

## Mocking

**Framework:** unittest.mock (not used in this codebase)

**Patterns:**
```python
# Dependency injection for testing - pass fakes instead of real implementations
class FakeAdapter:
    def __init__(self, name: str, response: AgentResponse):
        self.name = name
        self._response = response

    def run(self, prompt: str) -> AgentResponse:
        return self._response
```

**Callable injection for external dependencies:**
```python
class CommandJsonAdapter:
    def __init__(
        self,
        name: str,
        command_template: str,
        runner: Callable[[list[str]], str] = _default_runner  # Injected dependency
    ):
        self.runner = runner
```

**Test using fake runner:**
```python
def test_command_json_adapter_parses_structured_output(self) -> None:
    def fake_runner(args: list[str]) -> str:
        self.assertEqual(args[0], "fake-agent")
        self.assertIn("Solve safely", args)
        return json.dumps({...})

    adapter = CommandJsonAdapter("agent_a", "fake-agent {prompt}", fake_runner)
    result = adapter.run("Solve safely")
```

**Fake/stub implementations:**
- `FakeAdapter`: Returns pre-configured AgentResponse - used to test orchestrator
- `TrackingOrchestrator`: Records all calls made to it - used to verify action invocation
- Inline `fake_runner` functions: Return JSON strings for testing command parsing
- Inline `fake_input`/`fake_print` functions: Inject input/output for interactive code testing
- Inline `fake_which` function: Stub `shutil.which` to simulate agent availability

**What to Mock:**
- External command execution (subprocess) → use callable injection
- User input (input()) → pass fake input function
- File system operations (Path, file I/O) → use tempfile and real filesystem in tests
- Agent adapters → use FakeAdapter or custom stub

**What NOT to Mock:**
- AgentResponse, Disagreement, SessionResult models → use real dataclasses
- Classification logic → test actual logic, not mocked versions
- JSON parsing/serialization → test with real json module
- File storage (JsonlSessionStore) → use real tempfile for integration testing

## Fixtures and Factories

**Test Data:**
- AgentResponse creation: Used inline in tests to create different response configurations
  ```python
  AgentResponse(
      answer="Use queue workers.",
      proposed_actions=["Add queue", "Add retries"],
      assumptions=["Infra available"],
      confidence=0.81,
  )
  ```
- Mock orchestrator result: Created as inline dict or type object with attributes
  ```python
  session = type("Session", (), {
      "prompt": "base prompt",
      "agent_a": AgentResponse(...),
      "agent_b": AgentResponse(...),
      "disagreements": [type("D", (), {"kind": "approach", "summary": "..."})()],
  })()
  ```

**Location:**
- Test data is created inline in each test method
- No shared test fixtures or factory classes
- Temporary directories created with `tempfile.TemporaryDirectory()` context manager
- Real file I/O to `tmp_path` directories for integration testing

## Coverage

**Requirements:** Not specified - no coverage tool configured

**View Coverage:**
- Coverage not enforced or reported in build
- No `pytest-cov` or similar in dependencies

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes
- Approach: Test behavior with various inputs
- Examples:
  - `test_classifier_labels_approach_and_confidence_gap`: Tests `classify_disagreements()` classification logic
  - `test_command_json_adapter_parses_structured_output`: Tests JSON parsing in CommandJsonAdapter
  - `test_command_json_adapter_rejects_invalid_output`: Tests error handling

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Use real implementations with test doubles for external dependencies
- Examples:
  - `test_orchestrator_runs_and_persists_session`: Tests orchestrator + store together with fake adapters
  - `test_store_appends_multiple_sessions`: Tests JsonlSessionStore writes to real files
  - `test_build_reconcile_and_debate_prompts`: Tests prompt building with full session object
  - `test_apply_action_runs_follow_up_prompt`: Tests action application with tracking orchestrator

**E2E Tests:**
- Framework: Not used
- These would test full CLI workflow but are not implemented in current test suite

## Common Patterns

**Async Testing:**
- Async/await: Not used in this codebase
- Threading is used (ThreadPoolExecutor in DisagreementOrchestrator) but tests don't explicitly wait; the `run()` method is synchronous from caller's perspective

**Error Testing:**
```python
def test_command_json_adapter_rejects_invalid_output(self) -> None:
    def fake_runner(_: list[str]) -> str:
        return "not-json"

    adapter = CommandJsonAdapter("agent_b", "fake-agent {prompt}", fake_runner)
    with self.assertRaises(ValueError):
        adapter.run("anything")
```

**Parameter Validation Testing:**
```python
def test_command_json_adapter_extracts_json_from_text_wrapper(self) -> None:
    def fake_runner(_: list[str]) -> str:
        return 'Result:\n```json\n{"answer":"A","proposed_actions":["x"],"assumptions":["y"],"confidence":0.7}\n```'

    adapter = CommandJsonAdapter("agent_b", "fake-agent {prompt}", fake_runner)
    result = adapter.run("anything")
    self.assertEqual(result.answer, "A")
    self.assertEqual(result.confidence, 0.7)
```

**Testing with Real Filesystem:**
```python
def test_orchestrator_runs_and_persists_session(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        store = JsonlSessionStore(tmp_path / "sessions.jsonl")

        # ... run orchestrator ...

        # Verify persisted data
        lines = (tmp_path / "sessions.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        persisted = json.loads(lines[0])
        self.assertEqual(persisted["prompt"], "How should we process jobs?")
```

**Testing Interactive Code:**
```python
def test_collect_two_agents_uses_defaults_and_custom(self) -> None:
    answers = iter([
        "claude",
        "",
        "custom_remote",
        "ssh prod 'codex exec ...' {prompt}",
    ])
    lines = []

    def fake_input(_: str) -> str:
        return next(answers)

    def fake_print(msg: str) -> None:
        lines.append(msg)

    first, second = collect_two_agents(
        input_fn=fake_input,
        print_fn=fake_print,
        detected=[{"name": "claude"}, {"name": "codex"}],
        schema_path="schemas/agent_response.schema.json",
    )
    self.assertEqual(first["name"], "claude")
```

## Test Coverage Summary

**18 test cases covering:**
- Classification logic (3 tests)
- Orchestrator + Store integration (2 tests)
- Command adapter JSON parsing (3 tests)
- Prompt building (1 test)
- Action application (1 test)
- Launcher/CLI helper functions (8 tests)

**Coverage areas:**
- Happy path: All major features tested
- Error cases: Invalid JSON, missing fields, invalid index
- Edge cases: JSON wrapped in markdown, bare agent names
- Configuration: Saving/loading agent configs, detecting available agents
- Interactive flows: Multi-prompt user input sequences

**Not covered:**
- Full CLI entry point (`main()` in `cli.py`)
- Full launcher entry point (`run_interactive()` in `launcher.py`)
- ThreadPoolExecutor concurrency in DisagreementOrchestrator (executes real agents)
- Actual subprocess execution (mocked with fake_runner)

---

*Testing analysis: 2026-02-21*
