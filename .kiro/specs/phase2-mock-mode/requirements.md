# Phase 2 Mock Mode — Requirements

## Overview
Mock mode enables full offline development and testing of the navigation planner
without Bedrock API access or physical hardware. Activated via `--mock` flag in
`main.py` or by using `MockPolicy` directly.

## Functional Requirements

### FR-1: --mock CLI Flag
- `python main.py --mock` activates mock mode
- Creates `MockPolicy` via `create_policy("mock")`
- Welcome screen shows `[MOCK — no Bedrock / no hardware]` instead of model ID
- All REPL functionality works identically to live mode

### FR-2: MockPolicy Behaviour
- `plan()` ignores `user_request` entirely — returns fixed canned plan
- Default canned plan: `[{"action": "forward", "seconds": 2.0}, {"action": "stop"}]`
- Custom plan injectable via constructor: `MockPolicy(canned_plan={...})`
- `provider_name` returns `"mock"`
- Never calls Bedrock, never calls hardware

### FR-3: validate_plan() Still Called
- `main.py` calls `validate_plan(plan)` after `policy.plan()` even in mock mode
- This ensures the canned plan is always schema-valid
- `plan_navigation()` is NOT called in mock mode (it would call Bedrock)

### FR-4: Full REPL Flow in Mock Mode
- Pattern display works (print_patterns())
- Physics display works (print_physics())
- Plan display works (print_plan())
- Confirmation gate works (y/N prompt)
- Result display works (print_results())
- Only difference: no Bedrock call, no hardware call

### FR-5: MockPolicy for Testing
- Can be used in unit tests without any AWS credentials
- Can be used to test the full execution pipeline with a known plan
- Custom canned plan allows testing specific step sequences

### FR-6: No Mock Mode in app_ui.py
- The web UI does not support `--mock` flag (it's a server, not a CLI)
- Mock mode is only available in `main.py`
- To test the web UI offline, use a mock DeepRacer or stub the tool functions

## Non-Functional Requirements
- NFR-1: Mock mode must work with zero network access
- NFR-2: Mock mode must work with no `.env` file (no credentials needed)
- NFR-3: Mock mode output is visually identical to live mode output
- NFR-4: `MockPolicy` is deterministic — same input always produces same plan
