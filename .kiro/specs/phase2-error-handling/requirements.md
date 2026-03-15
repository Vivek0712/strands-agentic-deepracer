# Phase 2 Error Handling — Requirements

## Overview
Phase 2 introduces a unified error handling strategy: `is_error()` as single source of
truth, `stop_on_failure=True` as default, emergency stop on any hardware failure, and
SSE error events for the web UI. Every error path must surface to the user.

## Functional Requirements

### FR-1: is_error() Convention
- `is_error(message: str) -> bool` in `deepracer_tools.py` is the ONLY error detector
- Logic: `message.lower().startswith("error") or "stop_car failed" in message.lower()`
- Imported by `agent.py` and `deepracer_agent_tool.py`
- `app_ui.py` MUST NOT import or call `is_error()` — it uses inline ok computation instead

### FR-2: stop_on_failure=True Default
- Both `execute_plan()` and `execute_plan_full()` default to `stop_on_failure=True`
- On step failure: immediately call `execute_step({"action": "stop"})` as emergency
- Append emergency result to output with `"[emergency]"` prefix in message
- Then break — do not continue iterating remaining steps

### FR-3: Emergency Stop Pattern
- Emergency stop step: `{"action": "stop"}` executed via `execute_step()`
- Result appended as `(emergency_step, f"[emergency] {emergency.message}")`
- In `execute_plan_full()`: `result.aborted = True`, `result.abort_reason = sr.message`
- In `deepracer_agent_tool.py`: `await asyncio.to_thread(deepracer_stop)` called directly

### FR-4: Tool Function Error Returns
- All `@tool` functions return error strings starting with `"Error"` on failure
- They never raise exceptions to callers
- `execute_step()` wraps tool calls in try/except — exceptions become `StepResult(ok=False)`

### FR-5: Planning Error Handling
- `plan_navigation()` raises exceptions on JSON parse failure or validation failure
- `main.py` catches these and prints the error, then continues the REPL loop
- `app_ui.py` catches these and returns `{"ok": false, "error": str(exc)}` with 500
- `deepracer_agent_tool.py` catches these and sets `TaskStatus.ERROR`

### FR-6: Connection Error Handling
- `_get_client()` raises `RuntimeError` when password is empty
- `_move_for_duration()` catches client creation errors and returns error string
- `deepracer_connect()` catches all exceptions and returns error string
- `deepracer_agent_tool.py` checks `is_error(connect_msg)` and aborts to ERROR state

### FR-7: SSE Error Events
- Step failure in web UI: `step` event with `ok: false`
- Emergency stop: `step` event with `emergency: true`
- User abort: `stopped` event with message
- Hardware stop failure: included in stop response message, not raised

### FR-8: Cleanup Error Handling
- `DeepRacerTool.cleanup()` wraps everything in try/except
- `__del__` calls `cleanup()` in try/except — never raises from destructor
- `_action_stop()` catches hardware stop exceptions and includes in response

## Non-Functional Requirements
- NFR-1: No error path silently discards failures — every error surfaces to the user
- NFR-2: `DEEPRACER_PASSWORD` never appears in any error message
- NFR-3: Hardware errors trigger emergency stop before any other error handling
- NFR-4: The finally-block bug from Phase 1 is fixed — stop_car failure is a warning, not silent
