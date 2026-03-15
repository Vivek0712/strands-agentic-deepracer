---
inclusion: fileMatch
fileMatchPattern: "phase-3-adaptive-visual-navigation/deepracer_agent_tool.py"
---

# Phase 3: deepracer_agent_tool.py — Steering

## Phase 3 Additions to DeepRacerTool

### Vision Detection
- `self._has_vision = hasattr(policy, "has_vision") and policy.has_vision`
- Set in `__init__` — transparent upgrade; Phase 2 policies have no `has_vision` attribute

### New Methods

#### `_should_assess(action, step_seconds) -> bool`
- Returns False for "stop" and "connect" actions
- Returns False when `step_seconds < VISION_MIN_STEP_SECS` (default 0.5 s)
- Returns True otherwise — triggers vision check before step execution

#### `_assess_and_decide(step, original_instruction, step_index, total_steps, steps_remaining, replan_count, result) -> str`
- Gets latest frame: `self._policy.camera_stream.get_latest_frame()`
- Returns "continue" immediately if frame is None
- Builds `AssessContext` from parameters
- Calls `asyncio.wait_for(asyncio.to_thread(self._policy.assess_step, frame, context), timeout=VISION_ASSESS_TIMEOUT)`
- On `asyncio.TimeoutError`: logs warning, returns "continue"
- Appends `VisionEvent` to `self._task_state.vision_log`
- Pushes "vision" SSE event via `_push()`
- On "abort": calls `deepracer_stop()`, pushes "vision_abort" event, returns "abort"
- On "replan" (when `replan_count < MAX_REPLANS`): calls `policy.plan(new_instruction)`, validates, stores in `self._pending_replan_steps`, pushes "replan" event, returns "replan"
- On replan failure: logs warning, returns "continue"
- Returns "continue" for all other cases

#### `_execute_approved_plan(plan) -> None` (async)
- Used by `app_ui.py /execute` route — runs an already-validated plan
- Same vision loop as `_execute_task_async` but skips the planning step
- Reads `plan.get("_instruction_hint", plan.get("pattern", ""))` as `original_instruction`

### Main Execution Loop Pattern
```python
while remaining_steps:
    if self._task_state.status != TaskStatus.RUNNING: break
    if self._shutdown_event.is_set(): break

    step = remaining_steps[0]
    if self._has_vision and self._should_assess(action, step_seconds):
        outcome = await self._assess_and_decide(...)
        if outcome == "abort": break
        if outcome == "replan":
            remaining_steps = list(self._pending_replan_steps)
            replan_count += 1
            continue

    sr = await asyncio.to_thread(execute_step, step)
    remaining_steps.pop(0)
    if not sr.ok:
        await asyncio.to_thread(deepracer_stop)
        break
```

### New SSE Events (Phase 3)
- `"vision"` — `{step, action, reasoning, confidence}`
- `"vision_abort"` — `{reasoning}`
- `"replan"` — `{count, instruction, new_steps, pattern}`
- `"start"` now includes `"vision": bool`
- `"done"` now includes `"replan_count": int`

### New State Fields (Phase 3)
- `DeepRacerTaskState.vision_log: List[VisionEvent]`
- `DeepRacerTaskState.replan_count: int`
- `VisionEvent` dataclass: `step_index`, `action`, `reasoning`, `confidence`, `triggered_replan`

## Inherited Phase 2 Rules (all still apply)
- `_shutdown_event.is_set()` checked at top of every loop iteration
- `stop_on_failure=True` — hardware errors call `deepracer_stop()` before break
- `TaskStatus` state machine unchanged
- `ThreadPoolExecutor(max_workers=1)` unchanged
- `cleanup()` must call `_action_stop()` if RUNNING/PLANNING/CONNECTING
