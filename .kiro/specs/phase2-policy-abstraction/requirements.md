# Phase 2 Policy Abstraction — Requirements

## Overview
A clean policy abstraction layer that decouples the planning backend from the execution
pipeline. Enables offline development (`MockPolicy`), saved manoeuvre replay (`ReplayPolicy`),
and live Bedrock planning (`NovaPolicy`) through a common interface.

## Functional Requirements

### FR-1: NavigationPolicy Abstract Base
- `NavigationPolicy` is an abstract class with two required members:
  - `plan(user_request: str) -> Dict[str, Any]` — returns a validated plan dict
  - `provider_name -> str` property — identifies the backend
- Subclasses MUST implement both; calling the base raises `NotImplementedError`

### FR-2: NovaPolicy
- Wraps `create_planner()` + `plan_navigation()` from `agent.py`
- Constructor accepts optional `model: str` — falls back to `os.getenv("MODEL", DEFAULT_MODEL)`
- `provider_name` returns the resolved model ID string
- `plan()` calls `plan_navigation(self._agent, user_request)` which internally validates

### FR-3: MockPolicy
- Returns a fixed canned plan — never calls Bedrock or hardware
- Constructor accepts optional `canned_plan: Dict` — defaults to a simple forward+stop plan
- `provider_name` returns `"mock"`
- Used with `--mock` flag in `main.py` for offline development

### FR-4: ReplayPolicy
- Constructor takes `library: Dict[str, Dict]` — a named manoeuvre dictionary
- Keys are normalised to lowercase on construction
- `plan(user_request)` looks up `user_request.strip().lower()` in the library
- Raises `ValueError` with available keys listed when key not found
- `provider_name` returns `"replay"`

### FR-5: create_policy() Factory
- `create_policy(provider: str = "nova", **kwargs) -> NavigationPolicy`
- Supported providers: `"nova"`, `"mock"`, `"replay"`
- Raises `ValueError` with available providers listed for unknown provider
- `**kwargs` are forwarded to the policy constructor
- Callers MUST use this factory — never instantiate policies directly

## Non-Functional Requirements
- NFR-1: `MockPolicy` must work with zero network access (no Bedrock, no hardware)
- NFR-2: `ReplayPolicy` must be deterministic — same key always returns same plan
- NFR-3: All policies return plans that pass `validate_plan()` — callers may re-validate
- NFR-4: Policy selection is the only place where provider strings are resolved
