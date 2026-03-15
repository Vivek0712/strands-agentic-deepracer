# Phase 2: AgentTool Navigation Planner — Implementation Tasks

## Task 1: Module Constants (agent.py)
- [ ] `DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"`
- [ ] `MAX_STEP_SECONDS = float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))`
- [ ] `MAX_PLAN_STEPS = 20`
- [ ] `VALID_ACTIONS = frozenset({"connect","forward","backward","left","right","stop"})`
- [ ] `DEGREES_PER_SECOND = 90.0 / 1.5`
- [ ] `SECONDS_PER_DEGREE = 1.5 / 90.0`
- [ ] `FULL_ROTATION_SECS = (360.0 / 90.0) * 1.5`
- [ ] `_CLOSED_LOOP_PATTERNS` frozenset with all closed-loop pattern names
- [ ] `_ROTATION_TOLERANCE_DEG = 5.0`

## Task 2: PLANNER_PROMPT
- [ ] Role declaration + JSON-only output instruction
- [ ] Required JSON format with `_reasoning`, `pattern`, `steps` fields
- [ ] All 6 action names with descriptions and seconds rules
- [ ] Vehicle physics section (min radius, max corner speed, forward/turn speeds)
- [ ] Rotation calibration formula + reference table (60°→1.0s through 360°→6.0s)
- [ ] FULL ROTATION CHECK box with VERIFY step requirement
- [ ] All 15 named patterns with verified rotation math and step templates
- [ ] 8-point mandatory chain-of-thought section
- [ ] Worked examples for: tight circle, large circle (A+B), square, triangle, figure-8, slalom, spiral-out

## Task 3: Policy Classes
- [ ] `NavigationPolicy` abstract base with `plan()` and `provider_name`
- [ ] `NovaPolicy.__init__(model)` → `create_planner(model)`
- [ ] `NovaPolicy.plan()` → `plan_navigation(self._agent, user_request)`
- [ ] `MockPolicy.__init__(canned_plan)` with default forward+stop plan
- [ ] `MockPolicy.plan()` → returns `self._plan` regardless of input
- [ ] `ReplayPolicy.__init__(library)` → lowercases all keys
- [ ] `ReplayPolicy.plan()` → lookup or raise `ValueError`
- [ ] `create_policy(provider, **kwargs)` factory with `{"nova","mock","replay"}` table

## Task 4: Planner + Parsing
- [ ] `create_planner(model)` → `Agent(model=m, tools=[], system_prompt=PLANNER_PROMPT)`
- [ ] `_strip_fences(text)` using `re.sub` for both opening and closing fences
- [ ] `plan_navigation(planner, user_request)` → call → handle dict/str → validate → return

## Task 5: validate_plan()
- [ ] Check `isinstance(plan, dict)` → ValueError
- [ ] Check `"steps"` exists and is non-empty list → ValueError
- [ ] Warn if `_reasoning` missing or empty
- [ ] Warn if `len(steps) > MAX_PLAN_STEPS`
- [ ] Per-step: check dict, check action in VALID_ACTIONS, check seconds rules
- [ ] Check last step is `"stop"` → ValueError
- [ ] Call `_check_rotation(plan)` at end

## Task 6: _check_rotation()
- [ ] Sum all left/right step durations
- [ ] Compute total_degrees = total_turn_secs × DEGREES_PER_SECOND
- [ ] For figure-8: expected = 720°; for closed-loop patterns: expected = 360°
- [ ] Emit `warnings.warn` if deviation > `_ROTATION_TOLERANCE_DEG`

## Task 7: StepResult + PlanResult dataclasses
- [ ] `StepResult(step, ok, message)` with `display()` method
- [ ] `PlanResult(results, aborted, abort_reason, pattern, reasoning)` with `all_ok` and `completed_steps` properties

## Task 8: execute_step()
- [ ] Dispatch dict for all 6 actions
- [ ] Clamp seconds: `min(float(raw_sec), MAX_STEP_SECONDS)` with fallback 2.0
- [ ] Wrap tool call in try/except → StepResult(ok=False) on exception
- [ ] Use `is_error(str(msg))` to set ok
- [ ] Return StepResult(ok=False) for unknown actions

## Task 9: execute_plan() + execute_plan_full()
- [ ] `execute_plan()` returns `List[Tuple[dict, str]]`
- [ ] `execute_plan_full()` returns `PlanResult` with pattern/reasoning populated
- [ ] Both: on failure with stop_on_failure=True → emergency stop → break
- [ ] Emergency stop result appended with `"[emergency]"` prefix in execute_plan()

## Task 10: Verification
- [ ] `python --mock` runs without Bedrock or hardware
- [ ] `validate_plan` rejects plan with last step not "stop"
- [ ] `validate_plan` rejects step with seconds > 5.0
- [ ] `_check_rotation` warns on 8× left(1.5) circle (720° instead of 360°)
- [ ] `execute_plan` stops after first failure and appends emergency stop
