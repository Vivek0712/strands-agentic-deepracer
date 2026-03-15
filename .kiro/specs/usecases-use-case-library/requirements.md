# Spec: Use Case Library

## Overview
The use case library is the collection of all `{use_case}.py` files in `use_cases/`. Each file adapts a specific robot platform to the common tool interface.

## Requirements

### REQ-1: Completeness
The library MUST include implementations for all platforms listed in `use_cases/README.md`:
`deepracer`, `drone`, `boat`, `robot_arm`, `pipeline_crawler`, `roomba`, `lawnmower`, `hospital_cart`, `solar_inspection`, `rover`, `camera_dolly`, `underwater_rov`

### REQ-2: API Family Consistency
- MAVLink use cases (drone, boat, underwater_rov) MUST use DroneKit + pymavlink
- ROS2 use cases (roomba, lawnmower, hospital_cart, solar_inspection, rover) MUST use rosbridge WebSocket + `/cmd_vel`
- TCP use cases (pipeline_crawler, camera_dolly) MUST use raw TCP socket with JSON commands
- HTTP use cases (deepracer) MUST use the platform SDK

### REQ-3: Connection Caching
Every use case MUST cache its connection object in a module-level variable (`_CLIENT`, `_VEHICLE`, `_WS`, or `_SOCK`) and expose `reset_client()` to clear it.

### REQ-4: .env Loading
Every use case MUST call `load_dotenv()` at module level. The `.env` file MUST be in `use_cases/` or the use case's own directory.

### REQ-5: Rotation Calibration Documentation
Every use case MUST document its rotation calibration in the module docstring:
- The angular rate (deg/s or rad/s)
- The expected angle for the default `turn_left(1.5)` call
- Which env vars affect the calibration

### REQ-6: Vision Prompt Compatibility
Every use case MUST work with the default `VisionAssessor` system prompt. Use cases with domain-specific hazards SHOULD document a recommended `VISION_SYSTEM_PROMPT` in their module docstring.

### REQ-7: README Currency
`use_cases/README.md` MUST list every use case in the "Available Use Cases" table with correct platform, API, camera, and turning model columns.
