# Phase 2 Plan Validation — Tasks

## Task 1: Audit all hard-error conditions
- [ ] Not a dict → ValueError
- [ ] Missing/non-list steps → ValueError
- [ ] Empty steps → ValueError
- [ ] Step not a dict → ValueError
- [ ] Unknown action → ValueError with allowed list
- [ ] connect/stop with seconds → ValueError
- [ ] seconds not a number → ValueError
- [ ] seconds <= 0 → ValueError
- [ ] seconds > MAX_STEP_SECONDS → ValueError with "Split into shorter steps" message
- [ ] Last step not "stop" → ValueError

## Task 2: Audit soft warnings
- [ ] Missing/empty `_reasoning` → warnings.warn
- [ ] Steps > MAX_PLAN_STEPS → warnings.warn with count

## Task 3: Verify _check_rotation() warning conditions
- [ ] Confirm `_CLOSED_LOOP_PATTERNS` frozenset contains all 8 patterns
- [ ] Confirm figure-8 uses 720° expected (not 360°)
- [ ] Confirm tolerance is 5° (not hardcoded elsewhere)
- [ ] Confirm warning is emitted, not raised
- [ ] Confirm warning message includes actual vs expected degrees

## Task 4: Verify rotation math constants
- [ ] `DEGREES_PER_SECOND = 90.0 / 1.5` = 60.0
- [ ] `SECONDS_PER_DEGREE = 1.5 / 90.0` ≈ 0.01667
- [ ] `FULL_ROTATION_SECS = (360.0 / 90.0) * 1.5` = 6.0
- [ ] These are the ONLY place these values are defined — no hardcoding elsewhere

## Task 5: Test validate_plan() with edge cases
- [ ] Plan with connect step having seconds → rejected
- [ ] Plan with stop step having seconds → rejected
- [ ] Plan with 5.1s step → rejected with split message
- [ ] Plan with 5.0s step → accepted
- [ ] Plan ending with forward → rejected
- [ ] Valid minimal plan: `[{"action": "stop"}]` → accepted

## Task 6: Test _check_rotation() with known patterns
- [ ] circle with 4×1.5s turns → no warning (360° exact)
- [ ] circle with 3×1.5s turns → warning (270° ≠ 360°)
- [ ] figure-8 with 8×1.5s turns → no warning (720° exact)
- [ ] custom pattern → no rotation check
