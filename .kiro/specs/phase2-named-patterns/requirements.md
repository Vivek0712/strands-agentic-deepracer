# Phase 2 Named Patterns — Requirements

## Overview
A library of 15 pre-verified navigation patterns baked into the planner prompt.
Each pattern has verified rotation math, stabilisation rules applied, and step counts
within the 20-step cap. The LLM selects the closest named pattern or uses "custom".

## Functional Requirements

### FR-1: Pattern Library (15 patterns)
All patterns must appear in `PLANNER_PROMPT` with verified rotation math.

| Pattern | Total turn degrees | Key constraint |
|---|---|---|
| circle (tight) | 360° | 4 × left/right(1.5) |
| circle (large, option A) | 360° | 4 × [fwd(F) + left/right(1.5)] |
| circle (large, option B) | 360° | 8 × [fwd(F) + left/right(0.75)] |
| u-turn | 180° | 2 × right/left(1.5) |
| figure-8 | 720° | 4×left(1.5) + stabilise + 4×right(1.5) |
| square | 360° | 4 × [fwd(S) + right(1.5)] |
| triangle | 360° | 3 × [fwd(S) + right(2.0)] |
| pentagon | 360° | 5 × [fwd(S) + right(1.2)] |
| hexagon | 360° | 6 × [fwd(S) + right(1.0)] |
| oval | 360° | fwd(3.0) + right(3.0) + fwd(3.0) + right(3.0) |
| slalom (N gates) | 0° net | N × [left(T) + fwd(0.3) + fwd(G) + right(T) + fwd(0.3) + fwd(G)] |
| chicane | 0° net | left(1.0) + fwd(0.3) + right(1.0) |
| lane-change left | 0° net | left(1.0) + fwd(0.3) + right(1.0) |
| lane-change right | 0° net | right(1.0) + fwd(0.3) + left(1.0) |
| spiral-out | 360° per ring | 2 rings: inner fwd(0.5), outer fwd(1.5) |
| zigzag | 0° net | N × [left(1.5) + fwd(0.3) + right(1.5) + fwd(0.3)] |
| parallel-park | ~0° net | backward + right + backward + left + forward |
| figure-forward | 360° | fwd(3.0) + 4×right(1.5) + fwd(3.0) |

### FR-2: Stabilisation Rule
- After ANY left→right or right→left direction reversal, insert `{"action":"forward","seconds":0.3}`
- This applies to: figure-8 (transition), slalom (each gate), chicane, lane-change, zigzag
- The stabilisation step lets chassis flex settle before the next arc

### FR-3: Step Count Constraint
- All patterns must fit within 20 steps (including stop)
- Spiral-out: 2-ring version = 17 steps ✓; 3-ring = 25 steps → exceeds cap, use 2-ring only
- Slalom 3 cones: 1 + 3×6 + stop = 20 steps ✓ (at the limit)

### FR-4: Pattern Field in Plan JSON
- Every plan includes `"pattern": "<name>"` field
- Value is the closest named pattern or `"custom"` for novel manoeuvres
- Value is `"abort"` when the instruction is unsafe or ambiguous
- `_check_rotation()` uses this field to select expected degrees

### FR-5: Abort Pattern
- Unsafe or ambiguous instructions → `{"_reasoning":"...","pattern":"abort","steps":[{"action":"stop"}]}`
- This is a valid plan (passes `validate_plan()`) — last step is stop

### FR-6: Wrong Pattern Anti-Examples
- PLANNER_PROMPT MUST include explicit "✗ WRONG (never use)" examples for:
  - Circle: 8×left(1.5) = 720° (two rotations, not one)
  - Large circle: 8×[fwd+left(1.5)] = 720° (two rotations)

## Non-Functional Requirements
- NFR-1: Pattern rotation math must be verified before adding to the library
- NFR-2: New patterns must include the VERIFY step in their worked example
- NFR-3: Pattern names in `_check_rotation()` must match names used in the prompt exactly
