---
inclusion: fileMatch
fileMatchPattern: "phase-2-strands-robots-deepracer/agent.py"
---

# Phase 2: agent.py — Coding Standards & Patterns

## Module Constants
- `DEFAULT_MODEL`, `MAX_STEP_SECONDS`, `MAX_PLAN_STEPS`, `VALID_ACTIONS` are module-level constants
- `DEGREES_PER_SECOND = 90.0 / 1.5` and `SECONDS_PER_DEGREE = 1.5 / 90.0` are the single source of truth for rotation math — never hardcode these values elsewhere
- `FULL_ROTATION_SECS = (360.0 / 90.0) * 1.5` = 6.0 s — used by `_check_rotation()`

## PLANNER_PROMPT
- Must be a module-level string constant — never constructed dynamically
- Must contain all 8 chain-of-thought points in the MANDATORY section
- Must contain the full rotation calibration table
- Must contain all 15 named patterns with verified rotation math
- Must contain the FULL ROTATION CHECK box with the mandatory VERIFY step
- Must specify `stop` as the mandatory last step with no `seconds` field
- Must specify `MAX_STEP_SECONDS` (5.0 s) as the per-step cap
- Must specify the stabilisation rule: `forward(0.3)` after any left↔right reversal

## Policy Abstraction
- `NavigationPolicy` is abstract — subclasses implement `plan(user_request) -> Dict` and `provider_name -> str`
- `NovaPolicy` wraps `create_planner()` + `plan_navigation()`
- `MockPolicy` returns a fixed canned plan — never calls Bedrock
- `ReplayPolicy` looks up by key in a dict — raises `ValueError` for unknown keys
- `create_policy(provider, **kwargs)` is the factory — use it, never instantiate policies directly

## plan_navigation()
- Calls `planner(user_request)`, handles both dict and string responses
- Uses `_strip_fences()` (regex-based, handles any language hint) before `json.loads()`
- Calls `validate_plan()` before returning — plan is always validated
- Never mutates the returned dict

## validate_plan()
- Hard errors (raise `ValueError`): not a dict, missing/empty steps, step not a dict, unknown action, `connect`/`stop` with seconds, seconds ≤ 0, seconds > MAX_STEP_SECONDS, last step not `stop`
- Soft warnings (`warnings.warn`): missing `_reasoning`, steps > MAX_PLAN_STEPS
- Calls `_check_rotation()` at the end — rotation mismatch is a warning, not an error

## execute_step()
- Returns `StepResult` — never raises
- Uses a dispatch dict (not if/elif chain) for clean action routing
- Clamps seconds to `MAX_STEP_SECONDS` using `min(float(raw_sec), MAX_STEP_SECONDS)`
- Wraps the tool call in try/except — exceptions become `StepResult(ok=False)`
- Uses `is_error(str(msg))` from `deepracer_tools` to set `ok`

## execute_plan() vs execute_plan_full()
- `execute_plan()` returns `List[Tuple[dict, str]]` — compatible with `main.py` unpacking
- `execute_plan_full()` returns `PlanResult` — used by `deepracer_agent_tool.py`
- Both default `stop_on_failure=True`
- On failure: append emergency stop result, then break — do NOT continue iterating

## StepResult / PlanResult
- `StepResult.display()` formats one line with ✓/✗ icon, action, duration, message
- `PlanResult.all_ok` is True only when not aborted AND all steps ok
- `PlanResult.completed_steps` is `len(results)` — includes the failed step
