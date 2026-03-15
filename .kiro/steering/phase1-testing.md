---
inclusion: manual
---

# Phase 1 — Testing Guide

## Manual Test Scenarios

### CLI Tests (`python main.py`)

| Prompt | Expected Plan | Expected Behaviour |
|---|---|---|
| `Connect to the car` | `[{connect}]` | Shows vehicle info or connection string |
| `Move forward 3 seconds` | `[{forward, 3.0}]` | Car moves forward 3s then stops |
| `Move forward 2 seconds, turn left 1 second, then stop` | `[{forward,2},{left,1},{stop}]` | Sequential execution |
| `Do a full circle` | 4–8 × `{left}` or `{right}` steps | Car arcs in a circle |
| `Stop` | `[{stop}]` | Immediate stop command sent |
| (empty input) | — | Re-prompts silently |
| `help` | — | Prints example prompts |
| `exit` | — | Exits cleanly |
| Ctrl+C | — | Prints interrupted message, continues loop |
| `n` at confirm prompt | — | "Plan execution cancelled." |

### Web UI Tests (`python app_ui.py`)

| Action | Expected |
|---|---|
| Submit empty prompt | Plan button stays enabled, no request sent |
| Submit valid prompt | Plan panel appears with numbered steps |
| Click Cancel | Plan panel hides, currentPlan cleared |
| Click Execute | Result box shows "Done. N step(s) executed." in green |
| Network error (car off) | Result box shows error in red |
| Submit new prompt after execute | Chat history clears, new plan shown |

### API Tests (curl)

```bash
# Valid plan request
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Move forward 2 seconds"}'
# Expected: {"plan": {"steps": [{"action": "forward", "seconds": 2.0}]}}

# Empty prompt
curl -X POST http://localhost:5000/api/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt": ""}'
# Expected: 400 {"error": "prompt is required"}

# Valid execute
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"plan": {"steps": [{"action": "stop"}]}}'
# Expected: {"ok": true, "results": [{"step": 1, "action": "stop", "seconds": null, "ok": true}]}

# Missing plan
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 400 {"error": "plan with steps is required"}
```

## Environment Error Tests

```bash
# Missing password
DEEPRACER_PASSWORD= python -c "from deepracer_tools import deepracer_connect; print(deepracer_connect())"
# Expected: RuntimeError: DEEPRACER_PASSWORD is not set in environment

# Wrong IP (car unreachable)
DEEPRACER_IP=192.168.99.99 python -c "from deepracer_tools import deepracer_connect; print(deepracer_connect())"
# Expected: "Error creating DeepRacer client: ..." or connection timeout error string
```

## Dependency Check

```bash
cd phase-1-agentic-navigation-planner
python -c "from strands import Agent, tool; print('strands OK')"
python -c "import aws_deepracer_control_v2; print('deepracer control OK')"
python -c "from flask import Flask; print('flask OK')"
python -c "from dotenv import load_dotenv; print('dotenv OK')"
```
