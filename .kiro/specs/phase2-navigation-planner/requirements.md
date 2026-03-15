# Phase 2: AgentTool Navigation Planner — Requirements

## Overview
A physics-aware, pattern-driven DeepRacer controller built on the Strands AgentTool architecture. Extends Phase 1 with rotation math, 15 named patterns, plan validation, emergency stop on failure, async task management, and offline mock mode.

## Requirements

### REQ-P2-1: Policy Abstraction
- The system MUST provide a `NavigationPolicy` abstract base class with `plan(user_request) -> Dict` and `provider_name -> str`
- `NovaPolicy` MUST wrap `create_planner()` + `plan_navigation()` for live Bedrock inference
- `MockPolicy` MUST return a fixed canned plan without calling Bedrock — for offline testing
- `ReplayPolicy` MUST look up plans by key from a provided dict — raise `ValueError` for unknown keys
- `create_policy(provider, **kwargs)` MUST be the factory function — `"nova"`, `"mock"`, `"replay"` are valid providers

### REQ-P2-2: Physics-Aware Planner Prompt
- `PLANNER_PROMPT` MUST include empirically measured vehicle physics constants
- MUST include the rotation calibration formula: `duration = (angle / 90) × 1.5`
- MUST include the full reference table (60°→1.0s, 72°→1.2s, 90°→1.5s, 120°→2.0s, 180°→3.0s, 360°→6.0s)
- MUST include the FULL ROTATION CHECK box requiring a VERIFY step in `_reasoning`
- MUST include all 15 named patterns with pre-verified rotation math
- MUST require `_reasoning` field with 8 chain-of-thought points before any step
- MUST specify stabilisation rule: `forward(0.3)` after any left↔right or right↔left reversal
- MUST specify `stop` as mandatory last step with no `seconds` field
- MUST specify 5.0 s per-step cap

### REQ-P2-3: Plan Validation
- `validate_plan(plan)` MUST raise `ValueError` for: non-dict, missing/empty steps, unknown action, `connect`/`stop` with seconds, seconds ≤ 0, seconds > `MAX_STEP_SECONDS`, last step not `stop`
- MUST emit `warnings.warn` for: missing `_reasoning`, steps > `MAX_PLAN_STEPS` (20)
- MUST call `_check_rotation()` which warns when total turn time deviates > 5° from expected
- `plan_navigation()` MUST call `validate_plan()` before returning

### REQ-P2-4: Step Execution
- `execute_step(step)` MUST return `StepResult` — never raise
- MUST clamp seconds to `MAX_STEP_SECONDS` using `min(float(raw_sec), MAX_STEP_SECONDS)`
- MUST use a dispatch dict for action routing
- MUST use `is_error()` from `deepracer_tools` to set `StepResult.ok`
- Unknown actions MUST return `StepResult(ok=False, message="Unknown action '...' — skipped.")`

### REQ-P2-5: Plan Execution
- `execute_plan()` MUST return `List[Tuple[dict, str]]` for `main.py` compatibility
- `execute_plan_full()` MUST return `PlanResult` for `deepracer_agent_tool.py`
- Both MUST default `stop_on_failure=True`
- On failure with `stop_on_failure=True`: append emergency stop result, then break
- `execute_plan_full()` MUST populate `PlanResult.pattern` and `PlanResult.reasoning` from plan

### REQ-P2-6: DeepRacer Tools
- All 6 `@tool` functions MUST be present with correct default durations (turns: 1.5 s)
- `is_error(message)` MUST be a module-level function — single source of truth
- `reset_client()` MUST set `_CLIENT = None` to force fresh connection
- `_move_for_duration()` MUST NOT `return` inside `finally` — use `stop_warning` pattern
- Physics constants (`PHYSICS_*`) MUST be module-level and exported

### REQ-P2-7: AgentTool Interface
- `DeepRacerTool(AgentTool)` MUST expose 4 actions: `execute`, `start`, `status`, `stop`
- `action=execute` MUST be blocking (waits for completion)
- `action=start` MUST be non-blocking (submits to ThreadPoolExecutor)
- `action=status` MUST return current `TaskStatus`, pattern, steps, elapsed time
- `action=stop` MUST set status to STOPPED and call `deepracer_stop()` on hardware
- `stream()` MUST yield exactly one `ToolResultEvent` per invocation

### REQ-P2-8: Task State Machine
- `TaskStatus` enum MUST have: IDLE, CONNECTING, PLANNING, RUNNING, COMPLETED, STOPPED, ERROR
- `_execute_task_async()` MUST check `_shutdown_event.is_set()` at start of every step iteration
- `_execute_task_async()` MUST check `self._task_state.status != RUNNING` at start of every step iteration
- `cleanup()` MUST: set shutdown_event → stop if active → executor.shutdown → reset_client

### REQ-P2-9: Terminal REPL
- `main.py` MUST support `--mock` flag (MockPolicy, no Bedrock/hardware)
- MUST support `--model <id>` flag to override Bedrock model
- MUST support `patterns`, `physics`, `help`, `exit` commands
- MUST display pattern name and `_reasoning` alongside steps in plan display
- MUST show per-step ✓/✗ icons in execution results

### REQ-P2-10: Web UI with SSE
- `app_ui.py` MUST expose: `GET /`, `POST /plan`, `POST /execute`, `POST /stop`, `GET /stream`
- `/execute` MUST return immediately and stream progress via SSE
- SSE MUST emit: `start`, `step`, `done`, `stopped` events
- `/plan` MUST capture and return rotation warnings from `validate_plan()`
- Dashboard MUST display physics constants and pattern list from template context
