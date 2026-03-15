# Phase 2 Rotation Calibration — Tasks

## Task 1: Verify calibration constants in agent.py
- [ ] `DEGREES_PER_SECOND = 90.0 / 1.5` — confirm value is 60.0
- [ ] `SECONDS_PER_DEGREE = 1.5 / 90.0` — confirm value ≈ 0.01667
- [ ] `FULL_ROTATION_SECS = (360.0 / 90.0) * 1.5` — confirm value is 6.0
- [ ] No other file hardcodes 60.0, 0.01667, or 6.0 as rotation constants

## Task 2: Verify reference table in PLANNER_PROMPT
- [ ] 60° → 1.0 s present
- [ ] 72° → 1.2 s present
- [ ] 90° → 1.5 s present
- [ ] 120° → 2.0 s present
- [ ] 180° → 3.0 s present
- [ ] 270° → 4.5 s with split note present
- [ ] 360° → 6.0 s with split note present

## Task 3: Verify _check_rotation() uses constants (not literals)
- [ ] Uses `DEGREES_PER_SECOND` (not 60.0)
- [ ] Uses `FULL_ROTATION_SECS` (not 6.0)
- [ ] Uses `SECONDS_PER_DEGREE` for tolerance conversion
- [ ] Uses `_ROTATION_TOLERANCE_DEG = 5.0` (not hardcoded)

## Task 4: Verify .env calibration warning
- [ ] `.env` contains comment warning that changing STEER_ANGLE or TURN_THROTTLE invalidates calibration
- [ ] `.env.example` (if present) has the same warning

## Task 5: Verify pattern rotation math in PLANNER_PROMPT
- [ ] Circle: 4 × 1.5 = 6.0 s → 360° ✓
- [ ] Square: 4 × 1.5 = 6.0 s → 360° ✓
- [ ] Triangle: 3 × 2.0 = 6.0 s → 360° ✓
- [ ] Pentagon: 5 × 1.2 = 6.0 s → 360° ✓
- [ ] Hexagon: 6 × 1.0 = 6.0 s → 360° ✓
- [ ] Figure-8: 8 × 1.5 = 12.0 s → 720° ✓
- [ ] Oval: 2 × 3.0 = 6.0 s → 360° ✓

## Task 6: Test _check_rotation() warning threshold
- [ ] 5.0° deviation → no warning (at tolerance boundary)
- [ ] 5.1° deviation → warning emitted
- [ ] Correct circle plan → no warning
- [ ] Wrong circle plan (3×1.5 = 270°) → warning with clear message

## Task 7: Document re-calibration procedure
- [ ] Steps to re-measure: set up physical car, run timed turn, measure actual angle
- [ ] Update only `DEGREES_PER_SECOND` and `SECONDS_PER_DEGREE` in agent.py
- [ ] Re-verify all 15 patterns after any calibration change
