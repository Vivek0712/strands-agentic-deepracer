---
inclusion: fileMatch
fileMatchPattern: "use_cases/drone.py"
---

# Use Cases — MAVLink Robots Reference (drone, boat, underwater_rov)

## Shared Pattern
All MAVLink use cases use DroneKit + pymavlink. Connection object cached in module-level `_VEHICLE`.

```python
_VEHICLE = None

def _get_vehicle():
    global _VEHICLE
    if _VEHICLE is None:
        from dronekit import connect as dk_connect
        _VEHICLE = dk_connect(CONNECTION, wait_ready=True, timeout=30)
    return _VEHICLE

def reset_client() -> None:
    global _VEHICLE
    if _VEHICLE:
        try: _VEHICLE.close()
        except Exception: pass
    _VEHICLE = None
```

## drone.py
- `connect()` arms, sets GUIDED mode, and takes off to `DRONE_ALTITUDE` (default 1.5 m)
- `move_forward/backward` → `_send_ned_velocity(vx, vy=0, vz=0, duration)`
- `turn_left/right` → `_yaw(degrees, clockwise)` using `MAV_CMD_CONDITION_YAW`
- `stop()` → `_send_ned_velocity(0, 0, 0, 0.1)` — hover in place
- Rotation: `YAW_RATE` deg/s (default 30); `turn_left(1.5)` ≈ 45°
- Physics: `PHYSICS_MIN_TURN_RADIUS_M = 0.0` (yaw in place)

```
DRONE_CONNECTION   udp:127.0.0.1:14550
DRONE_ALTITUDE     1.5   (metres)
DRONE_SPEED        0.5   (m/s horizontal)
DRONE_YAW_RATE     30.0  (deg/s)
```

## boat.py
- `connect()` connects and reports GPS + battery — does NOT arm (boat stays on water)
- Movement via `_thrust(left, right, duration)` — RC channel override (ch3=left, ch1=right)
- `turn_left` → `_thrust(SPEED*0.2, SPEED, seconds)` (differential thrust)
- `turn_right` → `_thrust(SPEED, SPEED*0.2, seconds)`
- `stop()` → `_thrust(0.0, 0.0, 0.1)` — neutral RC
- Rotation: `YAW_RATE` deg/s (default 20); water resistance makes turns slower
- Physics: `PHYSICS_MIN_TURN_RADIUS_M = 1.5` (boats need space)

```
BOAT_CONNECTION   udp:127.0.0.1:14550
BOAT_SPEED        0.4   (0.0–1.0 throttle)
BOAT_YAW_RATE     20.0  (deg/s)
```

## is_error() for MAVLink use cases
```python
def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "cannot connect" in m
```

## activate_camera()
Both drone and boat return `True` immediately — cameras stream via RTSP/ROS2 without activation.

## Safety
- `stop()` MUST send zero-velocity or neutral RC before returning — never skip on exception
- `reset_client()` MUST call `_VEHICLE.close()` before clearing — prevents MAVLink socket leak
- DroneKit `connect()` blocks up to `timeout=30` — wrap in try/except in `connect()`
