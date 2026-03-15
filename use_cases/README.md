<div align="center">

# Use Cases

*One agentic navigation engine. Any robot.*

</div>

---

## Architecture

The Phase 3 codebase is split into two layers:

```
use_cases/
│
├── common/                    ← shared engine (hardware-agnostic)
│   ├── agent.py               planner + policy + vision constants
│   ├── vision_assessor.py     Nova Pro multimodal wrapper
│   ├── camera_stream.py       MJPEG frame buffer thread
│   ├── camera_policy.py       CameraPolicy orchestrator
│   ├── deepracer_agent_tool.py  execution loop
│   ├── app_ui.py              Flask web dashboard
│   ├── main.py                terminal REPL
│   └── templates/index.html   dashboard UI
│
├── common/base_tools.py       interface contract every use case must satisfy
│
├── deepracer.py               ← AWS DeepRacer (default)
├── warehouse_robot.py         ← Warehouse AMR via ROS2 /cmd_vel
├── drone.py                   ← MAVLink drone via DroneKit
├── robot_arm.py               ← 6-DOF arm via MoveIt2 + rosbridge
├── pipeline_crawler.py        ← Pipe inspection crawler via TCP
├── lawnmower.py               ← Autonomous lawnmower via ROS2
├── hospital_cart.py           ← Hospital delivery cart via ROS2
├── roomba.py                  ← iRobot Create3 via ROS2
├── camera_dolly.py            ← Motorised camera dolly via TCP
├── solar_inspection.py        ← Solar farm inspector via ROS2
├── boat.py                    ← Autonomous surface vessel via MAVLink
├── rover.py                   ← Outdoor exploration rover via ROS2
└── underwater_rov.py          ← Underwater ROV via ArduSub MAVLink
```

The only thing that changes per use case is the tool layer file. Everything else — the Nova Lite planner, Nova Pro vision assessor, MJPEG camera stream, SSE dashboard, and execution loop — is shared.

---

## How It Works

`agent.py` reads the `USE_CASE` environment variable and dynamically loads the corresponding `{use_case}.py` file:

```bash
USE_CASE=drone python main.py --vision
USE_CASE=warehouse_robot python app_ui.py
USE_CASE=pipeline_crawler python main.py --vision
```

The loaded module's functions are aliased to the names the execution engine expects:

```python
# In common/agent.py (auto-generated from USE_CASE):
deepracer_connect       = module.connect
deepracer_move_forward  = module.move_forward
deepracer_move_backward = module.move_backward
deepracer_turn_left     = module.turn_left
deepracer_turn_right    = module.turn_right
deepracer_stop          = module.stop
```

---

## Available Use Cases

| File | Platform | API | Camera | Turning model |
|------|----------|-----|--------|---------------|
| `deepracer.py` | AWS DeepRacer | aws-deepracer-control-v2 HTTP | USB MJPEG | Ackermann steering |
| `warehouse_robot.py` | AMR (MiR, Fetch, custom) | ROS2 `/cmd_vel` rosbridge | Any ROS2 cam | Differential drive — in place |
| `drone.py` | MAVLink drone (ArduPilot/PX4) | DroneKit + MAVLink UDP | Companion camera RTSP | Yaw in place |
| `robot_arm.py` | 6-DOF arm (UR5, Franka, custom) | MoveIt2 + rosbridge | Wrist/overhead camera | Wrist yaw rotation |
| `pipeline_crawler.py` | Pipe / duct inspection robot | TCP JSON serial | Endoscope MJPEG | Camera pan (robot cannot turn) |
| `lawnmower.py` | Autonomous lawnmower | ROS2 `/cmd_vel` rosbridge | Front RGB camera | Differential drive — in place |
| `hospital_cart.py` | Hospital delivery cart | ROS2 `/cmd_vel` rosbridge | Corridor RGB camera | Differential drive — in place |
| `roomba.py` | iRobot Create3 / Roomba | ROS2 `/cmd_vel` rosbridge | USB camera on top | Differential drive — in place |
| `camera_dolly.py` | Motorised camera dolly/slider | TCP JSON to motor controller | The mounted camera itself | Camera pan head (dolly is the camera) |
| `solar_inspection.py` | Solar farm inspection robot | ROS2 `/cmd_vel` rosbridge | Thermal + RGB downward | Differential drive — in place |
| `boat.py` | Autonomous surface vessel | MAVLink (ArduPilot Rover) | Waterproof forward camera | Differential thrust |
| `rover.py` | Outdoor exploration rover | ROS2 `/cmd_vel` rosbridge | Wide-angle front camera | Differential drive — in place |
| `underwater_rov.py` | Underwater ROV (BlueROV2) | MAVLink (ArduSub) UDP | Underwater front camera | Thruster yaw |

---

## Required Interface

Every `{use_case}.py` must export these names to work with the common engine.

### Functions

| Function | Signature | Description |
|---|---|---|
| `connect` | `() → str` | Connect to hardware, activate camera, return status string |
| `move_forward` | `(seconds: float) → str` | Move forward / towards target |
| `move_backward` | `(seconds: float) → str` | Move backward / retract |
| `turn_left` | `(seconds: float) → str` | Turn left / rotate CCW / pan left |
| `turn_right` | `(seconds: float) → str` | Turn right / rotate CW / pan right |
| `stop` | `() → str` | Immediate stop / hold position |
| `is_error` | `(message: str) → bool` | Return True if message indicates failure |
| `reset_client` | `() → None` | Clear cached connection |
| `activate_camera` | `() → bool` | Wake camera if needed; return True on success |

### Physics constants

| Name | Type | Description |
|---|---|---|
| `PHYSICS_MIN_TURN_RADIUS_M` | float | Minimum arc radius in metres (0.0 for in-place) |
| `PHYSICS_MAX_CORNER_SPEED` | float | Maximum safe speed during turns (m/s) |
| `PHYSICS_FWD_SPEED_MS` | float | Typical forward speed (m/s) |
| `PHYSICS_TURN_SPEED_MS` | float | Typical turning speed (m/s; 0.0 for in-place) |

### Optional metadata

```python
PLATFORM_NAME = "My Robot"         # shown in dashboard title
PLATFORM_DESC = "Brief description" # shown in dashboard subtitle
```

---

## Adding a New Use Case

1. Create `use_cases/{your_robot}.py`
2. Implement all required functions and constants
3. Test with the validator:

```python
from common.base_tools import load_tools, validate_tools

tools  = load_tools("your_robot")
errors = validate_tools(tools)
if errors:
    print(f"Missing: {errors}")
else:
    print("✓ Tool layer is valid")
```

4. Run:

```bash
cd use_cases
USE_CASE=your_robot python common/main.py --vision
```

### Minimal template

```python
# use_cases/my_robot.py

import os, time
from dotenv import load_dotenv
load_dotenv()

PLATFORM_NAME = "My Robot"
PLATFORM_DESC = "Brief description"

PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 1.0
PHYSICS_FWD_SPEED_MS      = 0.3
PHYSICS_TURN_SPEED_MS     = 0.0

def connect()                 -> str:  return "Connected."
def move_forward(seconds=2.0) -> str:  time.sleep(seconds); return f"Forward {seconds}s"
def move_backward(seconds=2.0)-> str:  time.sleep(seconds); return f"Backward {seconds}s"
def turn_left(seconds=1.5)    -> str:  time.sleep(seconds); return f"Left {seconds}s"
def turn_right(seconds=1.5)   -> str:  time.sleep(seconds); return f"Right {seconds}s"
def stop()                    -> str:  return "Stopped."
def is_error(msg: str)        -> bool: return str(msg).lower().startswith("error")
def reset_client()            -> None: pass
def activate_camera()         -> bool: return True
```

---

## Vision Prompt Customisation

Each use case benefits from a domain-specific vision system prompt. You can override the default in `common/vision_assessor.py` by setting `VISION_SYSTEM_PROMPT` in your `.env`:

```env
# For warehouse robot — only care about people and forklifts
VISION_SYSTEM_PROMPT="You are a safety monitor for a warehouse AMR. 
Stop immediately if you see a person or forklift. 
Replan if an aisle is blocked. Continue otherwise."
```

Or extend `VisionAssessor` and pass a custom system prompt at construction time:

```python
from common.vision_assessor import VisionAssessor

assessor = VisionAssessor(
    system_prompt="You are watching a pipeline inspection camera. 
    Abort if you see cracks, corrosion, or blockages."
)
```

---

## Environment Variables

Each use case reads its own `.env` file. Place a `.env` in `use_cases/` or in the same directory as the use case file.

Common variables (all use cases):

```env
AWS_REGION=us-east-1
MODEL=us.amazon.nova-lite-v1:0
VISION_MODEL=us.amazon.nova-pro-v1:0
VISION_TIMEOUT=4.0
MAX_REPLANS=3
VISION_MIN_STEP=0.3
```

Use-case-specific variables are documented in the header of each `{use_case}.py` file.
