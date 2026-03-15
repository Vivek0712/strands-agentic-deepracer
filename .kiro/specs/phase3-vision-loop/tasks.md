# Phase 3 Vision Loop — Tasks

## Task 1: Verify _should_assess() gate
- [ ] Returns False for action="stop"
- [ ] Returns False for action="connect"
- [ ] Returns False when step_seconds < VISION_MIN_STEP_SECS (default 0.5)
- [ ] Returns True for action="forward" with seconds=2.0
- [ ] Returns True for action="left" with seconds=1.5
- [ ] Handles None step_seconds without raising

## Task 2: Verify None frame short-circuit
- [ ] get_latest_frame() returns None → _assess_and_decide returns "continue"
- [ ] No API call made when frame is None
- [ ] No VisionEvent appended when frame is None

## Task 3: Verify asyncio.wait_for timeout
- [ ] asyncio.TimeoutError → logs warning, returns "continue"
- [ ] Timeout value is VISION_ASSESS_TIMEOUT (default 4.0 s)
- [ ] Execution continues normally after timeout

## Task 4: Verify "abort" decision handling
- [ ] Calls deepracer_stop() before returning "abort"
- [ ] Pushes "vision_abort" SSE event
- [ ] result.aborted = True set in main loop
- [ ] result.abort_reason = "Vision: immediate hazard."

## Task 5: Verify "replan" decision handling
- [ ] replan_count < MAX_REPLANS checked before acting
- [ ] At limit: returns "continue" (does not replan)
- [ ] Calls policy.plan(new_instruction or original_instruction)
- [ ] validate_plan() called on new plan
- [ ] New steps stored in self._pending_replan_steps
- [ ] Main loop reads self._pending_replan_steps after "replan" return
- [ ] replan_count incremented in main loop
- [ ] Pushes "replan" SSE event with count, instruction, new_steps, pattern
- [ ] On plan() or validate_plan() exception: logs warning, returns "continue"

## Task 6: Verify VisionEvent logging
- [ ] VisionEvent appended to self._task_state.vision_log for every assessment
- [ ] triggered_replan=True when action=="replan" and replan executed
- [ ] vision_log reset to [] at start of each task

## Task 7: Verify _execute_approved_plan()
- [ ] Skips planning step — runs plan["steps"] directly
- [ ] Uses _instruction_hint or pattern as original_instruction
- [ ] Same vision loop as _execute_task_async
- [ ] Called via asyncio.run() in app_ui.py /execute route

## Task 8: Verify Phase 2 backward compatibility
- [ ] NovaPolicy has no has_vision attribute → _has_vision = False
- [ ] MockPolicy has no has_vision attribute → _has_vision = False
- [ ] When _has_vision=False, _should_assess() never called
- [ ] Execution loop identical to Phase 2 when vision disabled

## Task 9: Verify SSE events
- [ ] "start" event includes "vision": bool
- [ ] "vision" event includes step, action, reasoning, confidence
- [ ] "replan" event includes count, instruction, new_steps, pattern
- [ ] "done" event includes replan_count
