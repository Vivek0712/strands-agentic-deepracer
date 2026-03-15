# Phase 2: DeepRacerTool (AgentTool) — Requirements

## Overview
`DeepRacerTool` wraps the DeepRacer navigation system as a Strands `AgentTool`, enabling a higher-level Strands Agent to control the car through natural language with full async task management.

## Requirements

### REQ-TOOL-1: AgentTool Subclass
- MUST subclass `AgentTool` from `strands.tools.tools`
- MUST implement `tool_name`, `tool_type`, `tool_spec`, and `stream()` properties/methods
- `tool_spec` MUST define the 4-action enum interface

### REQ-TOOL-2: Four-Action Interface
- `execute` — blocking: plan + run full sequence, return when done
- `start` — non-blocking: submit to background thread, return immediately with confirmation
- `status` — poll: return current TaskStatus, pattern, steps completed/total, elapsed time
- `stop` — abort: set status to STOPPED, send hardware stop command

### REQ-TOOL-3: TaskStatus State Machine
- MUST have exactly 7 states: IDLE, CONNECTING, PLANNING, RUNNING, COMPLETED, STOPPED, ERROR
- Transitions MUST only happen inside `_execute_task_async()`
- `_action_stop()` MUST force STOPPED from any active state (RUNNING/PLANNING/CONNECTING)
- ERROR state MUST be set on any unhandled exception in `_execute_task_async()`

### REQ-TOOL-4: Threading
- MUST use `ThreadPoolExecutor(max_workers=1)` — one plan at a time
- MUST use `threading.Event` (`_shutdown_event`) checked every step iteration
- `_sync_wrapper()` MUST handle both sync and async calling contexts
- `action=start` MUST guard against already-running tasks

### REQ-TOOL-5: Execution Phases
- Phase 1 (CONNECTING): call `deepracer_connect()`, abort on `is_error()`
- Phase 2 (PLANNING): call `policy.plan()` + `validate_plan()`, abort on exception
- Phase 3 (RUNNING): iterate steps, check shutdown_event and status each iteration
- On step failure: call `deepracer_stop()`, set `result.aborted=True`, break

### REQ-TOOL-6: Response Format
- All action methods MUST return `{"status": "success"|"error", "content": [{"text": "..."}]}`
- `_build_payload()` MUST include: status icon, pattern, steps completed/total, duration, error if any, full step log
- `stream()` MUST yield exactly one `ToolResultEvent` per invocation

### REQ-TOOL-7: Cleanup
- `cleanup()` MUST: set shutdown_event → stop active task → executor.shutdown(wait=True, cancel_futures=True) → reset_client()
- `__del__` MUST call `cleanup()` in try/except — never raise from destructor
- `cleanup()` MUST be idempotent — safe to call multiple times

### REQ-TOOL-8: Logging
- MUST use `logging.getLogger(__name__)` — never `print()` for operational messages
- Task start, completion, and errors MUST be logged at INFO/ERROR level
- `cleanup()` completion MUST be logged at INFO level
