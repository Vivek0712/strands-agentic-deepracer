# Phase 1: DeepRacer Tools — Design

## Module Structure

```
deepracer_tools.py
│
├── Constants (from .env)
│   ├── IP, PASSWORD
│   ├── FWD_THROTTLE, TURN_THROTTLE, MAX_SPEED, STEER_ANGLE
│   └── _CLIENT = None
│
├── Private Helpers
│   ├── _get_client() → drctl.Client
│   ├── _ensure_motors_ready(client)
│   └── _move_for_duration(steering, throttle, seconds, max_speed) → str
│
└── Public @tool Functions
    ├── deepracer_connect() → str
    ├── deepracer_move_forward(seconds) → str
    ├── deepracer_move_backward(seconds) → str
    ├── deepracer_turn_left(seconds) → str
    ├── deepracer_turn_right(seconds) → str
    └── deepracer_stop() → str
```

## Call Flow: Movement

```
deepracer_move_forward(seconds=2.0)
    │
    ▼
_move_for_duration(steering=0.0, throttle=-0.3, seconds=2.0)
    │
    ├─ _get_client() → cached drctl.Client
    ├─ _ensure_motors_ready(client)
    │     ├─ client.set_manual_mode()  [try/except → warning]
    │     └─ client.start_car()        [try/except → warning]
    ├─ client.move(0.0, -0.3, 1.0)
    ├─ time.sleep(2.0)
    └─ finally: client.stop_car()
```

## Call Flow: Connect

```
deepracer_connect()
    │
    ├─ _get_client() → cached drctl.Client
    ├─ io.StringIO() + redirect_stdout
    ├─ client.show_vehicle_info()
    └─ return captured output (or fallback string)
```

## Steering / Throttle Reference

| Tool | steering | throttle |
|---|---|---|
| move_forward | 0.0 | -FWD_THROTTLE |
| move_backward | 0.0 | +FWD_THROTTLE |
| turn_left | -STEER_ANGLE | -TURN_THROTTLE |
| turn_right | +STEER_ANGLE | -TURN_THROTTLE |
| stop | — | — (direct stop_car) |

## Error Return Convention

All functions return strings. Error strings always start with `"Error "`:
```
"Error creating DeepRacer client: <exc>"
"Error during move: <exc>"
"Error calling stop_car: <exc>"
"Warning: stop_car failed after move: <exc>"
```

Callers detect errors with: `result.lower().startswith("error")`

## Extension Pattern

To add a new motion tool (e.g. `deepracer_spin`):
1. Add `@tool` decorated function
2. Call `_move_for_duration(steering, throttle, seconds)` with appropriate values
3. Import the new function in `agent.py`
4. Add `"spin"` to the `execute_step()` dispatch in `agent.py`
5. Add `"spin"` to `PLANNER_PROMPT` allowed actions list
