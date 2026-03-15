# Phase 2 Environment Config — Requirements

## Overview
Phase 2 introduces one new environment variable (`DEEPRACER_MAX_STEP_SECS`) and requires
the `.env` file to carry calibration warnings. All variables are loaded via `python-dotenv`
from a `.env` file in the same directory as each module.

## Functional Requirements

### FR-1: Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `MODEL` | `us.amazon.nova-lite-v1:0` | Bedrock model ID |
| `DEEPRACER_IP` | `192.168.0.3` | Car IP on local network |
| `DEEPRACER_PASSWORD` | (required) | DeepRacer web console password |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `DEEPRACER_MAX_STEP_SECS` | `5.0` | Hard cap per step (clamp + reject) |
| `DEEPRACER_FWD_THROTTLE` | `0.30` | Forward/backward speed |
| `DEEPRACER_TURN_THROTTLE` | `0.20` | Turn speed — must stay < 1.5 m/s |
| `DEEPRACER_MAX_SPEED` | `1.0` | Speed ceiling |
| `DEEPRACER_STEER_ANGLE` | `0.50` | Steering magnitude (half-lock) |

### FR-2: New Variable — DEEPRACER_MAX_STEP_SECS
- Default: `5.0` seconds
- Used in `agent.py`: `MAX_STEP_SECONDS = float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))`
- `validate_plan()` rejects steps exceeding this value
- `execute_step()` clamps seconds to this value as a secondary safety net
- Not present in Phase 1 — Phase 1 used a hardcoded 10.0 s limit

### FR-3: Calibration Warning in .env
- The `.env` file MUST contain a comment warning:
  ```
  # WARNING: Changing DEEPRACER_STEER_ANGLE or DEEPRACER_TURN_THROTTLE
  # invalidates the rotation calibration (1.5 s ≈ 90°).
  # Re-measure on the physical car before updating the planner prompt.
  ```

### FR-4: .env Loading
- Each module loads `.env` from its own directory:
  ```python
  load_dotenv(Path(__file__).resolve().parent / ".env")
  ```
- This ensures the correct `.env` is loaded regardless of working directory

### FR-5: Credential Safety
- `DEEPRACER_PASSWORD` MUST NOT appear in logs, error messages, or version control
- `.env` is listed in `.gitignore`
- `_get_client()` raises `RuntimeError` when `PASSWORD` is empty string

### FR-6: .env.example (if present)
- Should contain all variables with placeholder values
- Must include the calibration warning comment
- Must NOT contain real credentials

## Non-Functional Requirements
- NFR-1: All float env vars use `float(os.getenv(..., "default"))` — never `int()`
- NFR-2: Missing optional vars fall back to defaults silently
- NFR-3: Missing `DEEPRACER_PASSWORD` is only detected at connection time, not at import
