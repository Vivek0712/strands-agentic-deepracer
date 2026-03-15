# Phase 2 Rotation Calibration — Requirements

## Overview
The rotation calibration is an empirically measured constant that maps turn duration to
heading change. It is the single source of truth for all angle math in the planner prompt,
validator, and pattern library. It MUST NOT be changed without re-measuring on the physical car.

## Functional Requirements

### FR-1: Core Calibration Constant
- `1.5 s ≈ 90°` — empirically measured at `TURN_THROTTLE=0.20`, `STEER_ANGLE=0.50`
- Derived constants in `agent.py`:
  - `DEGREES_PER_SECOND = 90.0 / 1.5` = 60.0 °/s
  - `SECONDS_PER_DEGREE = 1.5 / 90.0` ≈ 0.01667 s/°
  - `FULL_ROTATION_SECS = (360.0 / 90.0) * 1.5` = 6.0 s
- These constants are the ONLY place the calibration is encoded — never hardcode 60.0 or 0.01667 elsewhere

### FR-2: Reference Table (baked into PLANNER_PROMPT)
| Angle | Duration | Use case |
|---|---|---|
| 60° | 1.0 s | Hexagon corner |
| 72° | 1.2 s | Pentagon corner |
| 90° | 1.5 s | Square corner, circle quarter |
| 120° | 2.0 s | Triangle corner |
| 180° | 3.0 s | U-turn, oval end |
| 270° | 4.5 s | Must split: 3.0 s + 1.5 s |
| 360° | 6.0 s | Must split into ≤5 s steps |

### FR-3: Formula in Prompt
- `angle = (duration / 1.5) × 90°`
- `duration = (angle / 90) × 1.5 s`
- Both formulas MUST appear in `PLANNER_PROMPT` verbatim

### FR-4: _check_rotation() Validation
- Sums all `left`/`right` step durations in the plan
- Converts to degrees using `DEGREES_PER_SECOND`
- Compares against expected degrees for the named pattern
- Emits `warnings.warn` (not ValueError) when deviation > `_ROTATION_TOLERANCE_DEG = 5.0°`
- Warning message shows: actual turn time, actual degrees, expected time, expected degrees

### FR-5: Calibration Invalidation Warning
- Changing `DEEPRACER_STEER_ANGLE` or `DEEPRACER_TURN_THROTTLE` invalidates the calibration
- The `.env` file MUST contain a comment warning about this
- The planner prompt MUST NOT be updated with new values without re-measuring

### FR-6: Pattern-Specific Expected Degrees
| Pattern | Expected total degrees |
|---|---|
| circle | 360° |
| square | 360° |
| triangle | 360° |
| pentagon | 360° |
| hexagon | 360° |
| oval | 360° |
| spiral-out | 360° per ring |
| figure-forward | 360° |
| figure-8 | 720° (two circles) |

### FR-7: Mandatory VERIFY Step in Reasoning
- Every plan's `_reasoning` MUST include a VERIFY step:
  - `"VERIFY: Xs → Y°. ✓"` when correct
  - `"VERIFY: WRONG, recalculating."` when incorrect, followed by corrected math
- `validate_plan()` warns (not errors) when `_reasoning` is missing

## Non-Functional Requirements
- NFR-1: Calibration constants must never be duplicated — single source of truth in `agent.py`
- NFR-2: Re-calibration requires physical measurement on the car — not a code change alone
- NFR-3: The 5° tolerance exists to allow minor floating-point rounding, not to mask real errors
