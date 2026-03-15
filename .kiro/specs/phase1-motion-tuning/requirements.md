# Phase 1: Motion Tuning — Requirements

## Overview
The DeepRacer's physical movement behaviour is controlled by four tunable parameters. This spec covers how they are configured, validated, and applied.

## Requirements

### REQ-MOTION-1: Parameter Definitions
| Parameter | Env Var | Default | Range | Effect |
|---|---|---|---|---|
| Forward throttle | `DEEPRACER_FWD_THROTTLE` | `0.3` | 0.0–1.0 | Speed for forward/backward moves |
| Turn throttle | `DEEPRACER_TURN_THROTTLE` | `0.2` | 0.0–1.0 | Speed during turns (slower than forward) |
| Max speed | `DEEPRACER_MAX_SPEED` | `1.0` | 0.0–1.0 | Speed cap passed to `client.move()` |
| Steer angle | `DEEPRACER_STEER_ANGLE` | `0.5` | 0.0–1.0 | Steering magnitude for left/right turns |

### REQ-MOTION-2: Application
- `FWD_THROTTLE` is used for `deepracer_move_forward` (negated) and `deepracer_move_backward` (positive)
- `TURN_THROTTLE` is used for `deepracer_turn_left` and `deepracer_turn_right` (negated)
- `MAX_SPEED` is passed as the third argument to `client.move(steering, throttle, max_speed)`
- `STEER_ANGLE` is used as the steering magnitude: `-STEER_ANGLE` for left, `+STEER_ANGLE` for right

### REQ-MOTION-3: Duration Constraints
- Minimum safe duration: `0.1` seconds (anything shorter is effectively a no-op)
- Recommended range: `1.0–3.0` seconds (enforced in PLANNER_PROMPT)
- Maximum allowed: `10.0` seconds — plans with `seconds > 10.0` MUST be clamped or rejected
- Default when unspecified: `2.0` seconds

### REQ-MOTION-4: Turn Behaviour
- Turns MUST always combine forward throttle with steering — no reverse turns
- `left` = `steering=-STEER_ANGLE`, `throttle=-TURN_THROTTLE`
- `right` = `steering=+STEER_ANGLE`, `throttle=-TURN_THROTTLE`
- Turn throttle is intentionally lower than forward throttle for tighter turning radius

### REQ-MOTION-5: Full Circle Approximation
- "Full circle" / "u-turn" / "go around" MUST be approximated as multiple chained same-direction turn steps
- Each turn step in the sequence MUST use the standard `seconds` range (1.0–3.0s)
- The planner MUST NOT generate a single step claiming to turn a specific angle (e.g. "turn 360 degrees")
