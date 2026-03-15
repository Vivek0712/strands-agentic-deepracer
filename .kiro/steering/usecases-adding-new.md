---
inclusion: manual
---

# Use Cases — Adding a New Use Case

## Checklist

1. Create `use_cases/{your_robot}.py`
2. Implement all 9 required functions and 4 physics constants (see template below)
3. Validate with `validate_tools()` before running
4. Add a `.env` entry for any hardware-specific variables
5. Test with `--mock` first, then live hardware

## Minimal Template

```python
# use_cases/my_robot.py
import os, time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

PLATFORM_NAME = "My Robot"
PLATFORM_DESC = "One-line description"

# Physics — measure on real hardware before setting
PHYSICS_MIN_TURN_RADIUS_M = 0.0    # 0.0 = in-place; float("inf") = no turning
PHYSICS_MAX_CORNER_SPEED  = 1.0    # m/s
PHYSICS_FWD_SPEED_MS      = 0.3    # m/s
PHYSICS_TURN_SPEED_MS     = 0.0    # m/s (0.0 for in-place yaw)

_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None:
        # raise RuntimeError if required credentials are missing
        pass
    return _CLIENT

def reset_client() -> None:
    global _CLIENT
    _CLIENT = None

def is_error(message: str) -> bool:
    return str(message).lower().startswith("error")

def activate_camera() -> bool:
    return True  # return True if no camera or no activation needed

def connect() -> str:
    try:
        _get_client()
        return "Connected."
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        time.sleep(seconds)
        return f"Forward {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        time.sleep(seconds)
        return f"Backward {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        time.sleep(seconds)
        return f"Left {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        time.sleep(seconds)
        return f"Right {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        return "Stopped."
    except Exception as exc:
        return f"Error in stop: {exc}"
```

## Validation

```python
from use_cases.common.base_tools import load_tools, validate_tools

tools  = load_tools("my_robot")
errors = validate_tools(tools)
if errors:
    print(f"Missing: {errors}")
else:
    print("✓ Valid")
```

## Running

```bash
cd use_cases
USE_CASE=my_robot python common/main.py --mock    # offline test
USE_CASE=my_robot python common/main.py --vision  # live with camera
USE_CASE=my_robot python common/app_ui.py         # web UI
```

## Vision Prompt Customisation

Set `VISION_SYSTEM_PROMPT` in `.env` to tailor Nova Pro's assessment for your domain:

```env
VISION_SYSTEM_PROMPT="You are a safety monitor for a warehouse AMR. Stop if you see a person or forklift. Replan if an aisle is blocked."
```

Or subclass `VisionAssessor` and pass `system_prompt` at construction time.

## API Family Patterns

| API | Connection object | Stop pattern |
|-----|-------------------|--------------|
| HTTP REST | `requests.Session` or SDK client | Send zero-throttle or dedicated stop endpoint |
| MAVLink/DroneKit | `dronekit.Vehicle` | `_send_ned_velocity(0,0,0,0.1)` or RC neutral |
| ROS2 rosbridge | `websocket.WebSocket` | Publish zero `/cmd_vel` |
| TCP JSON | `socket.socket` | Send `{"cmd": "stop"}` |

## README Update

Add your robot to the table in `use_cases/README.md` under "Available Use Cases".
