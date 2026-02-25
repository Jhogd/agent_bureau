# Technology Stack

**Analysis Date:** 2026-02-21

## Languages

**Primary:**
- Python 3.10+ - Core application logic and CLI framework

## Runtime

**Environment:**
- Python 3.10+ (tested with 3.14.3)

**Package Manager:**
- pip (via setuptools)
- Lockfile: Not detected (no requirements.txt or constraints file present)

## Frameworks

**Core:**
- Standard library only - Uses built-in Python modules

**Testing:**
- pytest 8.0+ - Test discovery and execution
  - Config: `pyproject.toml` with pythonpath configuration

**Build/Dev:**
- setuptools 68+ - Package building and distribution
- wheel - Binary distribution format

## Key Dependencies

**Critical:**
- Python standard library: json, subprocess, shlex, pathlib, argparse, dataclasses, typing, concurrent.futures
  - These are built-in; no external packages required for core functionality

**Testing Only:**
- pytest 8.0+ - Optional dependency for development

## Configuration

**Environment:**
- No .env files detected
- No environment variable requirements
- Configuration is file-based (JSON) and command-line argument driven

**Build:**
- `pyproject.toml` - Project metadata and build configuration
  - Build backend: setuptools.build_meta
  - Python requirement: >=3.10

**Project Structure:**
- src/disagree_v1/ - Main package directory
- schemas/ - JSON schema files for agent response validation
- tests/ - Test suite directory
- .disagree/ - Runtime directory for session stores and agent configuration (created at runtime)

## Platform Requirements

**Development:**
- Python 3.10 or higher
- Unix-like shell (uses `shutil.which()` for agent detection on PATH)
- No external package dependencies required for core functionality

**Production:**
- Python 3.10 or higher
- External CLI tools (Claude, Codex) must be installed and available on system PATH
  - These are called via subprocess; not Python packages
  - Example: `claude`, `codex` commands must be executable and return JSON responses

## Schema Validation

**Agent Response Schema:**
- Location: `schemas/agent_response.schema.json`
- Format: JSON Schema (draft 2020-12)
- Used for: Validating JSON responses from external agent CLIs
- Fields: answer (string), proposed_actions (array[string]), assumptions (array[string]), confidence (number 0-1)

---

*Stack analysis: 2026-02-21*
