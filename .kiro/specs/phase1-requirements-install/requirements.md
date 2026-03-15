# Phase 1: Dependency Installation — Requirements

## Overview
Phase 1 has five Python dependencies. This spec covers what each does, why it's needed, and installation requirements.

## Requirements

### REQ-DEPS-1: Dependency List
All five MUST be listed in `phase-1-agentic-navigation-planner/requirements.txt`:

| Package | Purpose |
|---|---|
| `strands-agents` | Provides `Agent` class and `@tool` decorator |
| `strands-tools` | Additional Strands built-in tools (listed for completeness) |
| `python-dotenv` | Loads `.env` files into `os.environ` |
| `aws-deepracer-control-v2` | HTTP client for the DeepRacer web console API |
| `flask` | Web framework for `app_ui.py` |

### REQ-DEPS-2: Python Version
- Python 3.10+ is required (uses `str | None` union type syntax in `agent.py`)
- Python 3.12 is recommended for best compatibility with all packages

### REQ-DEPS-3: Installation Scope
- Dependencies MUST be installed inside the `phase-1-agentic-navigation-planner/` directory context
- A virtual environment is strongly recommended to avoid conflicts with other phases
- No version pins are required in `requirements.txt` unless a breaking change is encountered

### REQ-DEPS-4: AWS SDK
- `boto3` and `botocore` are NOT listed in `requirements.txt` — they are pulled in transitively by `strands-agents`
- Do NOT add them explicitly unless a version conflict requires pinning

### REQ-DEPS-5: No Dev Dependencies
- Phase 1 has no test framework, linter, or formatter dependencies in `requirements.txt`
- These may be added to a separate `requirements-dev.txt` if needed but MUST NOT be in the main file
