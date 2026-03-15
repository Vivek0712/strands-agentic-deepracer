---
inclusion: fileMatch
fileMatchPattern: "use_cases/common/base_tools.py"
---

# Use Cases — base_tools.py Reference

## Purpose
`base_tools.py` is the interface contract between the common engine and every use case tool file. It defines the `RobotTools` protocol, `load_tools()`, `validate_tools()`, and the canonical lists of required names.

## RobotTools Protocol
`RobotTools` is a `@runtime_checkable` `Protocol` — structural typing, no inheritance required. Any module that exposes the required names satisfies it. Use `isinstance(module, RobotTools)` to check at runtime.

## load_tools(use_case: str)
- Searches `use_cases/` then parent directory for `{use_case}.py`
- Uses `importlib.util.spec_from_file_location` — no package structure needed
- Registers module in `sys.modules[use_case]`
- Raises `ImportError` with a clear message if file not found — never returns None

```python
tools = load_tools("drone")       # loads use_cases/drone.py
tools = load_tools("deepracer")   # loads use_cases/deepracer.py
```

## validate_tools(module) → list[str]
- Returns list of missing required names — empty list means valid
- Checks all 9 functions + 4 physics constants from `REQUIRED_FUNCTIONS + REQUIRED_PHYSICS`
- Call this immediately after `load_tools()` before any execution

```python
tools  = load_tools("my_robot")
errors = validate_tools(tools)
if errors:
    raise RuntimeError(f"my_robot.py is missing: {errors}")
```

## REQUIRED_FUNCTIONS
```python
("connect", "move_forward", "move_backward", "turn_left", "turn_right",
 "stop", "is_error", "reset_client", "activate_camera")
```

## REQUIRED_PHYSICS
```python
("PHYSICS_MIN_TURN_RADIUS_M", "PHYSICS_MAX_CORNER_SPEED",
 "PHYSICS_FWD_SPEED_MS", "PHYSICS_TURN_SPEED_MS")
```

## Rules
- Do NOT add new required names without updating `REQUIRED_FUNCTIONS` or `REQUIRED_PHYSICS`
- Do NOT change `load_tools()` search order — `use_cases/` is checked before parent
- `validate_tools()` is the ONLY place to check interface completeness — never duplicate inline
