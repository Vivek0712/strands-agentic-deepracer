---
inclusion: fileMatch
fileMatchPattern: "use_cases/roomba.py"
---

# Use Cases — ROS2 /cmd_vel Robots Reference (roomba, lawnmower, hospital_cart, solar_inspection, rover)

## Shared Pattern
All ROS2 use cases publish to `/cmd_vel` via rosbridge WebSocket. Connection cached in module-level `_WS`.

```python
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{HOST}:{PORT}")
    return _WS

def _cmd_vel(linear_x: float, angular_z: float, duration: float) -> None:
    ws = _get_ws()
    ws.send(json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear":  {"x": linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0,      "y": 0.0, "z": angular_z},
    }}))
    time.sleep(duration)
    # Always send zero-velocity after duration
    ws.send(json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
    }}))

def reset_client() -> None:
    global _WS
    if _WS:
        try: _WS.close()
        except Exception: pass
    _WS = None
```

## Movement Mapping
- `move_forward(seconds)` → `_cmd_vel(LINEAR_VEL, 0.0, seconds)`
- `move_backward(seconds)` → `_cmd_vel(-LINEAR_VEL, 0.0, seconds)`
- `turn_left(seconds)` → `_cmd_vel(0.0, +ANGULAR_VEL, seconds)` — positive Z = CCW in ROS convention
- `turn_right(seconds)` → `_cmd_vel(0.0, -ANGULAR_VEL, seconds)`
- `stop()` → `_cmd_vel(0.0, 0.0, 0.1)` — zero-velocity pulse

## Rotation Calculation
```python
import math
deg = math.degrees(ANGULAR_VEL * seconds)  # degrees turned
```
All ROS2 use cases report degrees in their return strings using this formula.

## Per-Robot Config

| Use case | IP env var | Linear vel | Angular vel | Notes |
|----------|-----------|------------|-------------|-------|
| roomba | ROOMBA_IP (192.168.1.2) | ROOMBA_LINEAR_VEL=0.2 | ROOMBA_ANGULAR_VEL=1.0 rad/s | `stop()` also calls `_dock()` |
| lawnmower | LAWNMOWER_IP | LAWNMOWER_LINEAR_VEL=0.4 | LAWNMOWER_ANGULAR_VEL=0.5 | Outdoor, slower turns |
| hospital_cart | CART_IP | CART_LINEAR_VEL=0.3 | CART_ANGULAR_VEL=0.4 | Corridor-safe speed |
| solar_inspection | SOLAR_IP | SOLAR_LINEAR_VEL=0.3 | SOLAR_ANGULAR_VEL=0.5 | Row-following patterns |
| rover | ROVER_IP | ROVER_LINEAR_VEL=0.5 | ROVER_ANGULAR_VEL=0.4 | Outdoor terrain |

All use port 9090 (rosbridge default), overridable via `{PREFIX}_PORT`.

## Physics Constants (all ROS2 use cases)
```python
PHYSICS_MIN_TURN_RADIUS_M = 0.0   # differential drive — in-place rotation
PHYSICS_TURN_SPEED_MS     = 0.0   # yaw in place
```

## is_error() for ROS2 use cases
```python
def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m
```

## activate_camera()
All ROS2 use cases return `True` — cameras stream continuously via ROS2 topics, no activation needed.

## Safety
- `_cmd_vel()` MUST always send the zero-velocity message after `time.sleep(duration)` — even if the send raises, catch and log
- `stop()` MUST publish zero `/cmd_vel` before returning — this is the emergency stop
- `reset_client()` MUST close the WebSocket before clearing `_WS` — prevents socket leak
