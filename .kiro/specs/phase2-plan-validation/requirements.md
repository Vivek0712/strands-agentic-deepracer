# Phase 2 Plan Validation — Requirements

## Overview
`validate_plan()` is the gatekeeper between LLM output and hardware execution.
It enforces hard schema rules (ValueError), soft advisory warnings, and delegates
rotation consistency checking to `_check_rotation()`.

## Functional Requirements

### FR-1: Hard Errors (raise ValueError)
- Plan is not a dict
- Missing or non-list `steps` key
- Empty `steps` list
- Any step is not a dict
- Step has unknown `action` (not in VALID_ACTIONS)
- `connect` or `stop` step has a `seconds` field
- Movement step has `seconds` that is not a number
- Movement step has `seconds <= 0`
- Movement step has `seconds > MAX_STEP_SECONDS` — error message MUST say "Split into shorter steps"
- Last step action is not `"stop"`

### FR-2: Soft Warnings (warnings.warn)
- Plan has no `_reasoning` field or it is empty/whitespace
- Plan has more than `MAX_PLAN_STEPS` steps (currently 20)

### FR-3: Rotation Check
- `validate_plan()` calls `_check_rotation(plan)` at the end
- `_check_rotation()` emits a warning (never an error) when total turn time deviates from expected by > 5°
- Closed-loop patterns checked: circle, square, triangle, pentagon, hexagon, oval, spiral-out, figure-forward
- figure-8 expected: 720° (two full circles)
- All other closed-loop patterns expected: 360°
- Custom/unknown patterns: no rotation check

### FR-4: _check_rotation() Implementation
- Sums `seconds` of all `left` and `right` steps
- Converts to degrees: `total_degrees = total_turn_secs * DEGREES_PER_SECOND`
- Tolerance: `_ROTATION_TOLERANCE_DEG = 5.0` degrees
- Warning message includes: pattern name, actual turn time, actual degrees, expected time, expected degrees
- Warning stacklevel=3 so it points to the caller of validate_plan()

### FR-5: VALID_ACTIONS
- `frozenset({"connect", "forward", "backward", "left", "right", "stop"})`
- Checked case-insensitively (action is lowercased before comparison)

### FR-6: MAX_STEP_SECONDS
- Read from `DEEPRACER_MAX_STEP_SECS` env var, default 5.0
- Used in both `validate_plan()` (reject) and `execute_step()` (clamp)

## Non-Functional Requirements
- NFR-1: `validate_plan()` is called by `plan_navigation()` — plan is always validated before return
- NFR-2: `validate_plan()` is also called by `main.py` after `MockPolicy.plan()` (which skips it)
- NFR-3: `validate_plan()` must not mutate the plan dict
- NFR-4: Error messages must be human-readable and actionable
