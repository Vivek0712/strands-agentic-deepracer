---
inclusion: fileMatch
fileMatchPattern: "phase-2-strands-robots-deepracer/deepracer_agent_tool.py"
---

# Phase 2: deepracer_agent_tool.py — Coding Standards & Patterns

## Class Structure
- `DeepRacerTool` subclasses `AgentTool` from `strands.tools.tools`
- Constructor takes `policy: NavigationPolicy` and `tool_name: str = "deepracer"`
- `tool_spec` property returns the full ToolSpec dict with 4-action enum
- `stream()` is the Strands entry point — async generator yielding `ToolResultEvent`

## TaskStatus State Machine
```
IDLE → CONNECTING → PLANNING → RUNNING → COMPLETED
                                       ↘ STOPPED  (user abort via action=stop)
                                       ↘ ERROR    (exception or hardware failure)
```
- State transitions happen only inside `_execute_task_async()`
- `_action_stop()` forces state to STOPPED from any active state
- Never transition backwards (e.g. COMPLETED → RUNNING)

## Threading Model
- `ThreadPoolExecutor(max_workers=1)` — only one plan runs at a time
- `threading.Event` (`_shutdown_event`) — checked at start of every step loop iteration
- `action=execute` → `_sync_wrapper()` → blocks until `_execute_task_async()` completes
- `action=start` → `_executor.submit(_sync_wrapper, instruction)` → returns immediately
- `_sync_wrapper()` detects running event loop and handles both sync and async contexts

## _execute_task_async() Phases
1. CONNECTING — call `deepracer_connect()`, abort on `is_error()`
2. PLANNING — call `self._policy.plan(instruction)` + `validate_plan()`, abort on exception
3. RUNNING — iterate steps, check shutdown_event + status each iteration
4. On step failure: call `deepracer_stop()`, set `result.aborted=True`, break

## _build_payload()
- Returns `{"status": "success"|"error", "content": [{"text": "..."}]}`
- Includes pattern, steps completed/total, duration, error message if any
- Includes full step log from `sr.display()` for each StepResult

## Action Dispatch
- `action=execute` → `_action_execute(instruction)` → `_sync_wrapper(instruction)`
- `action=start` → `_action_start(instruction)` — guards against already-running task
- `action=status` → `_action_status()` — updates duration if RUNNING
- `action=stop` → `_action_stop()` — sends hardware stop regardless of state

## stream() Entry Point
- Extracts `action` and `instruction` from `tool_use["input"]`
- Validates `instruction` is present for execute/start
- Dispatches to action methods via a dict
- Yields exactly one `ToolResultEvent` per call
- Catches all exceptions and yields an error ToolResultEvent

## cleanup() / __del__
- `cleanup()`: set shutdown_event → stop if active → executor.shutdown(wait=True, cancel_futures=True) → reset_client()
- `__del__`: calls `cleanup()` in try/except — never raises from destructor
- Always call `cleanup()` explicitly when done — don't rely on `__del__`

## tool_spec Requirements
- `name` must match `self._tool_name_str`
- `action` enum must be exactly: `["execute", "start", "status", "stop"]`
- `instruction` is required for execute/start, optional for status/stop
- `required: ["action"]` — instruction is validated in stream(), not in schema
