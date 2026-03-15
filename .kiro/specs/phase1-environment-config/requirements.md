# Phase 1: Environment Configuration — Requirements

## Overview
All runtime configuration is managed through a `.env` file loaded by `python-dotenv`. This spec covers the full set of environment variables, their defaults, validation, and security requirements.

## Requirements

### REQ-ENV-1: Required Variables
- `DEEPRACER_PASSWORD` — MUST be set; absence MUST raise `RuntimeError` at client creation time (not silently ignored)
- `DEEPRACER_IP` — MUST default to `"192.168.0.3"` if not set

### REQ-ENV-2: Model Configuration
- `MODEL` — Bedrock model ID; MUST default to `"us.amazon.nova-lite-v1:0"`
- `AWS_REGION` — AWS region for Bedrock; MUST default to `"us-east-1"`

### REQ-ENV-3: Motion Tuning
All motion parameters MUST have safe numeric defaults:
| Variable | Default | Type | Purpose |
|---|---|---|---|
| `DEEPRACER_FWD_THROTTLE` | `0.3` | float | Forward/backward speed |
| `DEEPRACER_TURN_THROTTLE` | `0.2` | float | Turn speed |
| `DEEPRACER_MAX_SPEED` | `1.0` | float | Speed cap passed to `client.move()` |
| `DEEPRACER_STEER_ANGLE` | `0.5` | float | Steering angle magnitude for turns |

### REQ-ENV-4: Loading
- `.env` MUST be loaded using `load_dotenv(Path(__file__).resolve().parent / ".env")` in each module that needs it (`agent.py`, `deepracer_tools.py`, `main.py`)
- `.env.example` MUST be kept up to date with all variables and their defaults

### REQ-ENV-5: Security
- `.env` MUST be listed in `.gitignore`
- `DEEPRACER_PASSWORD` MUST never appear in logs, error messages, or API responses
- `.env.example` MUST use placeholder values (e.g. `your_password_here`), never real credentials

### REQ-ENV-6: Type Safety
- All float env vars MUST be cast with `float(os.getenv(..., "default"))` at module load time
- Invalid float values MUST cause a clear `ValueError` at startup, not silently use 0
