---
inclusion: always
---

# Use Cases — Project Overview

## Architecture

Two-layer design: shared engine in `use_cases/common/` + per-robot tool files in `use_cases/`.

```
use_cases/
├── common/                    ← hardware-agnostic engine (identical to Phase 3)
│   ├── agent.py               planner + policy + vision constants
│   ├── vision_assessor.py     Nova Pro multimodal wrapper
│   ├── camera_stream.py       MJPEG frame buffer thread
│   ├── camera_policy.py       CameraPolicy orchestrator
│   ├── deepracer_agent_tool.py  execution loop (vision + step tracking)
│   ├── app_ui.py              Flask web dashboard
│   ├── main.py                terminal REPL
│   ├── base_tools.py          RobotTools protocol + load_tools() + validate_tools()
│   └── templates/index.html   dashboard UI
│
├── deepracer.py               AWS DeepRacer (HTTP, Ackermann)
├── drone.py                   MAVLink drone (DroneKit, yaw-in-place)
├── boat.py                    MAVLink surface vessel (differential thrust)
├── robot_arm.py               6-DOF arm (MoveIt2 + rosbridge, Cartesian)
├── pipeline_crawler.py        Pipe crawler (TCP JSON, camera pan only)
├── roomba.py                  iRobot Create3 (ROS2 /cmd_vel, rosbridge)
├── lawnmower.py               Lawnmower (ROS2 /cmd_vel, rosbridge)
├── hospital_cart.py           Hospital cart (ROS2 /cmd_vel, rosbridge)
├── solar_inspection.py        Solar inspector (ROS2 /cmd_vel, rosbridge)
├── rover.py                   Outdoor rover (ROS2 /cmd_vel, rosbridge)
├── camera_dolly.py            Camera dolly (TCP JSON, pan head)
└── underwater_rov.py          BlueROV2 (ArduSub MAVLink)
```

## How Tool Loading Works

`USE_CASE` env var selects the tool file. `common/agent.py` calls `load_tools(use_case)` which dynamically imports `{use_case}.py` and aliases its functions to the names the engine expects:

```python
deepracer_connect      = module.connect
deepracer_move_forward = module.move_forward
deepracer_stop         = module.stop
# ... etc
```

The engine never imports a use case file directly — always via `load_tools()`.

## Running

```bash
cd use_cases
USE_CASE=deepracer python common/main.py           # default
USE_CASE=drone     python common/main.py --vision
USE_CASE=roomba    python common/app_ui.py
USE_CASE=boat      python common/main.py --mock
```

`USE_CASE` defaults to `deepracer` if unset.

## API Families

| API | Use cases | Transport |
|-----|-----------|-----------|
| aws-deepracer-control-v2 HTTP | deepracer | HTTP REST |
| MAVLink / DroneKit | drone, boat, underwater_rov | UDP/TCP |
| ROS2 /cmd_vel via rosbridge | roomba, lawnmower, hospital_cart, solar_inspection, rover | WebSocket |
| MoveIt2 via rosbridge | robot_arm | WebSocket |
| TCP JSON | pipeline_crawler, camera_dolly | TCP socket |

## Environment Variables (common to all use cases)

```env
AWS_REGION=us-east-1
MODEL=us.amazon.nova-lite-v1:0
VISION_MODEL=us.amazon.nova-pro-v1:0
VISION_TIMEOUT=4.0
MAX_REPLANS=3
VISION_MIN_STEP=0.3
```

Use-case-specific variables are documented in the header of each `{use_case}.py` file.
