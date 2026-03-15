# Phase 1: Full Circle / U-Turn Manoeuvre — Tasks

## Task 1: PLANNER_PROMPT Circle Rule
- [ ] Confirm PLANNER_PROMPT contains a rule for "full circle" / "go around completely" / "u-turn"
- [ ] Confirm the rule says to chain multiple same-direction turn steps (not a single large-angle step)
- [ ] Confirm the rule says NOT to generate steps like "turn 180 degrees" or "turn 360 degrees"
- [ ] Confirm the rule specifies consistent direction (all left or all right) for the sequence

## Task 2: Test Full Circle Plan Generation
- [ ] Submit "Do a full circle" — confirm plan has 4+ consecutive `"left"` or `"right"` steps
- [ ] Submit "Go around completely" — confirm same pattern
- [ ] Submit "Turn in a complete circle to the right" — confirm all steps are `"right"`
- [ ] Confirm no step in the circle plan has `"seconds"` > 3.0

## Task 3: Test U-Turn Plan Generation
- [ ] Submit "Do a u-turn" — confirm plan has 2–4 same-direction turn steps
- [ ] Submit "Turn around" — confirm similar pattern
- [ ] Confirm the u-turn plan has fewer steps than a full circle plan

## Task 4: Execution Test
- [ ] Execute a full circle plan on the car — confirm it completes all steps without stopping early
- [ ] Confirm each turn step calls `_move_for_duration` with the correct steering angle
- [ ] Confirm `stop_car()` is called after each individual turn step (in finally)
- [ ] Confirm the car does not get stuck between steps

## Task 5: Edge Cases
- [ ] Submit "Spin in place" — confirm plan uses turn steps (not a new "spin" action)
- [ ] Submit "Do 3 circles" — confirm plan has ~12+ chained turn steps
- [ ] Submit "Half circle" — confirm plan has ~2–4 turn steps
