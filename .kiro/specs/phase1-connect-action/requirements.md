# Phase 1: Connect Action — Requirements

## Overview
The `connect` action is the only non-movement action in Phase 1. It verifies the car is reachable, shows battery and vehicle info, and is typically the first step in any plan.

## Requirements

### REQ-CONNECT-1: Purpose
- `deepracer_connect()` MUST verify the DeepRacer is reachable at the configured IP
- It MUST display vehicle information (battery level, model info) when available
- It MUST be usable as a standalone plan: `{"steps": [{"action": "connect"}]}`

### REQ-CONNECT-2: Implementation
- MUST call `client.show_vehicle_info()` with stdout captured via `io.StringIO` + `redirect_stdout`
- MUST return the captured output if non-empty
- MUST return `f"Connected to DeepRacer at {IP}."` as fallback if output is empty
- MUST NOT print directly to stdout (captured output is returned as a string)

### REQ-CONNECT-3: No seconds Field
- The `connect` action MUST NOT include a `"seconds"` field in the plan
- `PLANNER_PROMPT` MUST specify: "For 'connect', omit 'seconds'"
- `execute_step()` MUST NOT pass `seconds` when calling `deepracer_connect()`

### REQ-CONNECT-4: Planner Usage
- The planner SHOULD include `connect` as the first step when the user says "connect to the car"
- The planner MAY include `connect` as the first step in any plan as a pre-flight check
- `connect` MUST be listed in `PLANNER_PROMPT`'s allowed actions with description "check connection / battery before moving"

### REQ-CONNECT-5: Error Handling
- If `_get_client()` fails: return `f"Error creating DeepRacer client: {exc}"`
- If `show_vehicle_info()` raises: return `f"Error calling show_vehicle_info: {exc}"`
- Both error strings MUST start with `"Error "` for consistent detection
