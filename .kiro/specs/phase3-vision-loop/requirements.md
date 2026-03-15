# Phase 3 Vision Loop — Requirements

## Overview
The vision loop lives in `deepracer_agent_tool.py`. It gates each plan step
behind a Nova Pro assessment when `CameraPolicy` is active. The loop is a
transparent upgrade — Phase 2 policies run identically when `has_vision` is absent.

## Functional Requirements

### FR-1: Vision detection in DeepRacerTool.__init__()
- `self._has_vision = hasattr(policy, "has_vision") and policy.has_vision`
- Set once at construction — not re-evaluated per step

### FR-2: _should_assess(action, step_seconds) -> bool
- Returns False when action is "stop" or "connect"
- Returns False when `step_seconds` is not None and `float(step_seconds) < VISION_MIN_STEP_SECS`
- Returns True otherwise
- Never raises — handles TypeError/ValueError from float() conversion

### FR-3: _assess_and_decide() -> str ("continue" | "replan" | "abort")
- Gets frame: `self._policy.camera_stream.get_latest_frame()`
- Returns "continue" immediately if frame is None (no API call)
- Builds `AssessContext` with all required fields
- Calls `asyncio.wait_for(asyncio.to_thread(self._policy.assess_step, frame, context), timeout=VISION_ASSESS_TIMEOUT)`
- On `asyncio.TimeoutError`: logs warning, returns "continue"
- Appends `VisionEvent` to `self._task_state.vision_log`
- Pushes "vision" SSE event: `{step, action, reasoning, confidence}`
- On "abort": calls `await asyncio.to_thread(deepracer_stop)`, pushes "vision_abort" event, returns "abort"
- On "replan" when `replan_count < MAX_REPLANS`:
  - Calls `await asyncio.to_thread(self._policy.plan, new_instruction or original_instruction)`
  - Calls `validate_plan(new_plan)`
  - Stores new steps in `self._pending_replan_steps`
  - Stores new pattern in `self._pending_replan_pattern`
  - Pushes "replan" SSE event: `{count, instruction, new_steps, pattern}`
  - Returns "replan"
  - On any exception: logs warning, returns "continue"
- Returns "continue" for all other cases (including replan limit reached)

### FR-4: Main execution loop (both _execute_task_async and _execute_approved_plan)
```
while remaining_steps:
    check status != RUNNING → abort
    check _shutdown_event.is_set() → abort

    if _has_vision and _should_assess(action, step_seconds):
        outcome = await _assess_and_decide(...)
        if outcome == "abort": break
        if outcome == "replan":
            remaining_steps = list(self._pending_replan_steps)
            replan_count += 1
            self._task_state.replan_count = replan_count
            self._task_state.total_steps = completed + len(remaining_steps)
            continue

    sr = await asyncio.to_thread(execute_step, step)
    remaining_steps.pop(0)
    if not sr.ok:
        await asyncio.to_thread(deepracer_stop)
        break
```

### FR-5: _execute_approved_plan(plan) async method
- Skips the planning step — runs `plan["steps"]` directly
- Uses `plan.get("_instruction_hint", plan.get("pattern", ""))` as `original_instruction`
- Same vision loop as `_execute_task_async`
- Called by `app_ui.py /execute` route via `asyncio.run()`

### FR-6: New SSE events
- `"vision"` — `{"step": int, "action": str, "reasoning": str, "confidence": float}`
- `"vision_abort"` — `{"reasoning": str}`
- `"replan"` — `{"count": int, "instruction": str, "new_steps": int, "pattern": str}`
- `"start"` — now includes `"vision": bool`
- `"done"` — now includes `"replan_count": int`

### FR-7: New state fields
- `DeepRacerTaskState.vision_log: List[VisionEvent]` — reset to [] at start of each task
- `DeepRacerTaskState.replan_count: int` — reset to 0 at start of each task
- `VisionEvent` dataclass: `step_index`, `action`, `reasoning`, `confidence`, `triggered_replan: bool`

## Non-Functional Requirements
- NFR-1: Vision timeout (VISION_ASSESS_TIMEOUT default 4.0 s) prevents blocking execution
- NFR-2: Phase 2 policies unaffected — no `has_vision` → loop runs identically to Phase 2
- NFR-3: All Phase 2 safety rules still apply — hardware failures still trigger emergency stop
