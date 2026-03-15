# Phase 2 Named Patterns — Tasks

## Task 1: Audit all 15 patterns in PLANNER_PROMPT
- [ ] circle (tight) — 4×1.5 = 6.0 s → 360° ✓
- [ ] circle (large, option A) — 4×1.5 = 6.0 s → 360° ✓
- [ ] circle (large, option B) — 8×0.75 = 6.0 s → 360° ✓
- [ ] u-turn — 2×1.5 = 3.0 s → 180° ✓
- [ ] figure-8 — 8×1.5 = 12.0 s → 720° ✓
- [ ] square — 4×1.5 = 6.0 s → 360° ✓
- [ ] triangle — 3×2.0 = 6.0 s → 360° ✓
- [ ] pentagon — 5×1.2 = 6.0 s → 360° ✓
- [ ] hexagon — 6×1.0 = 6.0 s → 360° ✓
- [ ] oval — 2×3.0 = 6.0 s → 360° ✓
- [ ] slalom — net 0° per gate ✓
- [ ] chicane — net 0° ✓
- [ ] lane-change left — net 0° ✓
- [ ] lane-change right — net 0° ✓
- [ ] spiral-out — 2 rings × 360° ✓
- [ ] zigzag — net 0° ✓
- [ ] parallel-park — net ~0° ✓
- [ ] figure-forward — 4×1.5 = 6.0 s → 360° ✓

## Task 2: Verify stabilisation steps are present
- [ ] figure-8: fwd(0.3) between left and right phases
- [ ] slalom: fwd(0.3) after each left and each right turn
- [ ] chicane: fwd(0.3) between left and right
- [ ] lane-change: fwd(0.3) between turns
- [ ] zigzag: fwd(0.3) between each reversal

## Task 3: Verify step counts ≤ 20
- [ ] spiral-out 2-ring: 4×2 + 4×2 + stop = 17 ✓
- [ ] slalom 3 cones: 1 + 3×6 + stop = 20 ✓
- [ ] figure-8: 4×2 + 2 + 4×2 + stop = 19 ✓
- [ ] All other patterns well under 20

## Task 4: Verify anti-examples are in PLANNER_PROMPT
- [ ] "✗ WRONG: 8×left(1.5) = 720°" for tight circle
- [ ] "✗ WRONG: 8×[fwd+left(1.5)] = 720°" for large circle

## Task 5: Verify _CLOSED_LOOP_PATTERNS matches prompt
- [ ] frozenset contains: circle, square, triangle, pentagon, hexagon, oval, spiral-out, figure-forward
- [ ] figure-8 handled separately with 720° expected
- [ ] slalom, chicane, lane-change, zigzag, parallel-park NOT in closed-loop set

## Task 6: Add a new pattern (workflow)
- [ ] Calculate rotation math: N sides × (360/N)° per corner
- [ ] Verify: total_turn_time × (90/1.5) = expected degrees
- [ ] Check step count ≤ 20
- [ ] Add stabilisation steps for any direction reversals
- [ ] Add to PLANNER_PROMPT with VERIFY annotation
- [ ] Add to `_CLOSED_LOOP_PATTERNS` if it's a closed loop
- [ ] Add to `print_patterns()` in main.py and patterns list in app_ui.py
