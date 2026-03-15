# Phase 1: Error Handling — Requirements

## Overview
Consistent error handling across all layers ensures the car never gets stuck in motion and users always receive actionable feedback.

## Requirements

### REQ-ERR-1: Tool Layer (deepracer_tools.py)
- All `@tool` functions MUST return strings — never raise to callers
- Error strings MUST be prefixed with `"Error "` (capital E, space after)
- Warning strings (non-fatal) MUST be prefixed with `"Warning: "`
- `_get_client()` is the ONLY place that raises — it raises `RuntimeError` for missing password
- `stop_car()` failure inside `finally` MUST return the warning string, not silently pass

### REQ-ERR-2: Agent Layer (agent.py)
- `plan_navigation()` MUST raise `ValueError` with a clear message if JSON parsing fails
- `plan_navigation()` MUST raise `ValueError` if `"steps"` is missing or not a list
- `execute_step()` MUST return a skip string for unknown actions — never raise
- `execute_plan()` MUST NOT raise — all step errors are captured as result strings

### REQ-ERR-3: CLI Layer (main.py)
- `create_planner()` failure MUST print `❌ Failed to create planner agent: <exc>` and exit
- `plan_navigation()` failure MUST print `❌ Failed to plan navigation: <exc>` and re-prompt
- Execution errors per step MUST be printed inline with the step result
- `KeyboardInterrupt` MUST be caught in the input loop — print a message and continue

### REQ-ERR-4: Web Layer (app_ui.py + index.html)
- `/api/plan` exceptions MUST return HTTP 500 with `{"error": "<message>"}`
- `/api/execute` exceptions MUST return HTTP 500 with `{"ok": false, "error": "<message>"}`
- Frontend fetch errors MUST display in the result box with the `error` CSS class (red)
- Network errors (fetch throws) MUST be caught and shown as `e.message || 'Request failed'`
- Per-step `ok: false` results MUST be visually distinguishable in the UI

### REQ-ERR-5: Error Detection Convention
- The string `result.lower().startswith("error")` is the canonical check for tool errors
- This convention MUST be used consistently in `app_ui.py` execute summary and any future callers
- Do NOT use exception-based error detection for tool results

### REQ-ERR-6: User-Facing Messages
- Error messages shown to users MUST be human-readable — no raw Python tracebacks
- Credential errors MUST NOT reveal the password value
- Network/connection errors MUST suggest checking `DEEPRACER_IP` and car power state
