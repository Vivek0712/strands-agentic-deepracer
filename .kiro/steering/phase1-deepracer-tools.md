---
inclusion: fileMatch
fileMatchPattern: "phase-1-agentic-navigation-planner/deepracer_tools.py"
---

# DeepRacer Tools — Coding Standards & Patterns

## Tool Registration
All public movement functions MUST be decorated with `@tool` from `strands`. This makes them discoverable by the Strands agent executor.

## Client Singleton
Use `_get_client()` to access the cached `drctl.Client`. Never instantiate `drctl.Client` directly outside this function. The singleton is module-level `_CLIENT`.

## Movement Pattern
All directional moves go through `_move_for_duration(steering, throttle, seconds, max_speed)`:
- Always call `_ensure_motors_ready(client)` before `client.move()`
- Always call `client.stop_car()` in a `finally` block after movement
- Return a descriptive string — never raise exceptions to callers

## Throttle Sign Convention
| Direction | Throttle sign |
|---|---|
| Forward | negative (e.g. -0.3) |
| Backward | positive (e.g. +0.3) |
| Turn left | negative throttle + negative steering |
| Turn right | negative throttle + positive steering |

## Environment Config
Read all tuning values from `.env` at module load time via `os.getenv()` with safe defaults:
- `DEEPRACER_FWD_THROTTLE` → `FWD_THROTTLE`
- `DEEPRACER_TURN_THROTTLE` → `TURN_THROTTLE`
- `DEEPRACER_MAX_SPEED` → `MAX_SPEED`
- `DEEPRACER_STEER_ANGLE` → `STEER_ANGLE`

## Error Handling
- Return error strings prefixed with `"Error ..."` — never raise
- Wrap `client.set_manual_mode()` and `client.start_car()` in try/except with a warning print
- `stop_car()` failures in `finally` should return the warning string, not swallow it

## Adding a New Tool
1. Define a function with `@tool` decorator
2. Add a clear docstring (used by the agent as tool description)
3. Route through `_move_for_duration()` if it involves motion
4. Export the function name in `agent.py` imports
