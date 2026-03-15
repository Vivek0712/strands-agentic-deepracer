# Phase 1: Full Circle / U-Turn Manoeuvre — Requirements

## Overview
"Do a full circle", "go around completely", and "u-turn" are common natural-language requests that require special handling in the planner prompt. The car cannot rotate in place — circles must be approximated as chained turn steps.

## Requirements

### REQ-CIRCLE-1: Prompt Instruction
- `PLANNER_PROMPT` MUST explicitly instruct the model how to handle circle/u-turn requests
- The instruction MUST specify: chain multiple same-direction turn steps (all `"left"` or all `"right"`)
- The instruction MUST forbid: a single step claiming to turn a specific angle (e.g. "turn 360 degrees")
- The instruction MUST specify: each step uses standard forward motion with steering

### REQ-CIRCLE-2: Step Count
- A full circle approximation SHOULD produce 4–8 chained same-direction turn steps
- Each step SHOULD use 1.0–2.0 seconds duration
- All steps in the sequence MUST use the same direction (all left or all right)

### REQ-CIRCLE-3: U-Turn Approximation
- A u-turn SHOULD produce 2–4 chained same-direction turn steps
- Total turning time SHOULD be approximately half that of a full circle

### REQ-CIRCLE-4: Executor Handling
- The executor (`execute_step`) handles circle steps as normal `"left"` or `"right"` actions
- No special-case code is needed in the executor for circles — the planner handles decomposition
- The plan for a circle is indistinguishable from any other multi-step turn sequence

### REQ-CIRCLE-5: Physical Behaviour
- The car turns in an arc (not in place) because turns use forward throttle
- The turning radius depends on `STEER_ANGLE` and `TURN_THROTTLE` values
- A true 360° circle requires sufficient space — the planner prompt should note this implicitly by using conservative step counts
