# CLAUDE.md

## Core Engineering Principles (SOLID)

### Single Responsibility Principle (SRP)
- Each class/module has exactly one reason to change.
- Separate business logic, persistence, formatting, and side effects.
- Avoid large files (>500 lines) and multi-purpose classes.
- Red flags: class names like `*Manager`, `*Handler`, or `*And`; methods doing unrelated tasks.

### Open/Closed Principle (OCP)
- Extend behavior without modifying existing, tested code.
- Prefer composition over inheritance.
- Use dependency injection and strategy patterns.
- When adding functionality, introduce new abstractions/implementations instead of editing stable logic.

### Liskov Substitution Principle (LSP)
- Subtypes must be safely substitutable for base types.
- Do not add stricter preconditions or unexpected exceptions.
- Avoid `NotImplementedError` in subclasses and runtime type checks (`isinstance`) to make subclasses work.

### Interface Segregation Principle (ISP)
- Prefer small, focused interfaces.
- Do not force clients to implement methods they do not use.
- Split large interfaces into role-specific interfaces and compose where needed.

### Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions, not concrete implementations.
- Inject dependencies rather than instantiating them directly.

## Test-Driven Development (TDD)

TDD is mandatory.

### Red-Green-Refactor workflow
1. **RED**: Write a failing test first.
2. **GREEN**: Write the minimum code to make the test pass.
3. **REFACTOR**: Improve structure/naming while keeping tests green.

### TDD rules
- No production code without a failing test.
- No extra functionality beyond what the test requires.

### Test quality standards
Tests must be:
- Fast
- Independent
- Repeatable
- Self-validating
- Written just before production code

Use AAA pattern:
- Arrange
- Act
- Assert

Test:
- Public interfaces
- Behavior and edge cases
- Integration points

Do not test:
- Private methods
- Third-party libraries
- Trivial getters/setters (unless logic exists)

## Commit Practices

### Frequency
- Commit after every Red-Green-Refactor cycle.
- Commit before and after refactoring.
- Commit at least every 30 minutes of active work.

### Commit message format
`<type>: <subject>`

Allowed types:
- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `style`
- `chore`

Rules:
- Imperative mood
- ≤ 50 characters
- No vague messages (e.g., "WIP")

Preferred TDD commit sequence:
1. `test: Add failing test for feature`
2. `feat: Implement feature to pass test`
3. `refactor: Improve structure and naming`

## Failure Handling
- If tests fail, do not commit.
- Fix code/tests, run full suite, then commit with a clear message.

## Daily Development Loop
1. Pull latest changes.
2. Run full test suite.
3. Write failing test.
4. Commit test.
5. Implement minimal solution.
6. Commit feature.
7. Refactor if needed.
8. Commit refactor.

## Self-Review Checklist
Before finalizing:

Design:
- Single responsibility per class
- Open for extension, closed for modification
- Proper abstractions and dependency injection

Tests:
- All tests pass
- New code has tests
- Edge cases are covered

Commits:
- Small, focused, descriptive
- Each commit builds and passes tests
- No debugging leftovers or commented-out dead code
