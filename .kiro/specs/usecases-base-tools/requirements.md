# Spec: Use Cases Base Tools

## Overview
The `base_tools.py` module provides the interface contract, dynamic loader, and validator that decouples the common engine from any specific robot hardware.

## Requirements

### REQ-1: RobotTools Protocol
- The `RobotTools` class MUST be a `@runtime_checkable` `Protocol`
- It MUST declare all 9 required functions and 4 physics constants as protocol members
- `isinstance(module, RobotTools)` MUST work at runtime without inheritance

### REQ-2: load_tools()
- MUST accept a `use_case: str` name (e.g. `"drone"`, `"deepracer"`)
- MUST search `use_cases/` directory first, then parent directory
- MUST use `importlib.util.spec_from_file_location` for dynamic loading
- MUST register the module in `sys.modules[use_case]`
- MUST raise `ImportError` with a descriptive message if the file is not found
- MUST never return `None`

### REQ-3: validate_tools()
- MUST accept a loaded module and return `list[str]` of missing names
- MUST check all entries in `REQUIRED_FUNCTIONS + REQUIRED_PHYSICS`
- Empty list MUST mean the module is fully valid
- MUST NOT raise — always returns a list

### REQ-4: REQUIRED_FUNCTIONS constant
Must contain exactly:
`("connect", "move_forward", "move_backward", "turn_left", "turn_right", "stop", "is_error", "reset_client", "activate_camera")`

### REQ-5: REQUIRED_PHYSICS constant
Must contain exactly:
`("PHYSICS_MIN_TURN_RADIUS_M", "PHYSICS_MAX_CORNER_SPEED", "PHYSICS_FWD_SPEED_MS", "PHYSICS_TURN_SPEED_MS")`

### REQ-6: Usage Pattern
The common engine MUST always call `load_tools()` then `validate_tools()` before any execution. Direct imports of use case files are forbidden in the common engine.
