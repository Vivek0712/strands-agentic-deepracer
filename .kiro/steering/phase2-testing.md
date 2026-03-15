---
inclusion: manual
---

# Phase 2: Testing Guide

## Offline Testing (no Bedrock, no hardware)

### Mock mode REPL
```bash
cd phase-2-strands-robots-deepracer
python main.py --mock
```
- Returns fixed canned plan: `[forward(2.0), stop]`
- All REPL commands work: `patterns`, `physics`, `help`
- Confirmation gate works: must type `y` or `yes`
- Hardware calls will fail gracefully (expected without a car)

### Custom mock plan
```python
from agent import create_policy, validate_plan

policy = create_policy("mock", canned_plan={
    "_reasoning": "Test.",
    "pattern": "square",
    "steps": [
        {"action": "forward", "seconds": 2.0},
        {"action": "right", "seconds": 1.5},
        {"action": "forward", "seconds": 2.0},
        {"action": "right", "seconds": 1.5},
        {"action": "forward", "seconds": 2.0},
        {"action": "right", "seconds": 1.5},
        {"action": "forward", "seconds": 2.0},
        {"action": "right", "seconds": 1.5},
        {"action": "stop"}
    ]
})
plan = policy.plan("anything")
validate_plan(plan)  # should pass
```

## validate_plan() Unit Tests

### Hard error cases (must raise ValueError)
```python
from agent import validate_plan

# Last step not stop
try:
    validate_plan({"steps": [{"action": "forward", "seconds": 2.0}]})
    assert False, "Should have raised"
except ValueError as e:
    assert "stop" in str(e).lower()

# Step exceeds MAX_STEP_SECONDS
try:
    validate_plan({"steps": [{"action": "forward", "seconds": 6.0}, {"action": "stop"}]})
    assert False, "Should have raised"
except ValueError as e:
    assert "split" in str(e).lower()

# connect with seconds
try:
    validate_plan({"steps": [{"action": "connect", "seconds": 1.0}, {"action": "stop"}]})
    assert False, "Should have raised"
except ValueError:
    pass
```

### Rotation warning cases
```python
import warnings
from agent import validate_plan

# Wrong circle (270° instead of 360°) — should warn
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    validate_plan({
        "pattern": "circle",
        "steps": [
            {"action": "left", "seconds": 1.5},
            {"action": "left", "seconds": 1.5},
            {"action": "left", "seconds": 1.5},
            {"action": "stop"}
        ]
    })
    assert len(w) > 0
    assert "rotation" in str(w[0].message).lower()

# Correct circle (360°) — no rotation warning
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    validate_plan({
        "pattern": "circle",
        "steps": [
            {"action": "left", "seconds": 1.5},
            {"action": "left", "seconds": 1.5},
            {"action": "left", "seconds": 1.5},
            {"action": "left", "seconds": 1.5},
            {"action": "stop"}
        ]
    })
    rotation_warnings = [x for x in w if "rotation" in str(x.message).lower()]
    assert len(rotation_warnings) == 0
```

## is_error() Tests
```python
from deepracer_tools import is_error

assert is_error("Error creating client") == True
assert is_error("error: connection refused") == True
assert is_error("Warning: stop_car failed after move") == True
assert is_error("stop_car failed") == True
assert is_error("Moved: steering=0.00 throttle=-0.30") == False
assert is_error("Connected to DeepRacer") == False
assert is_error("Stop command sent") == False
```

## StepResult / PlanResult Tests
```python
from agent import StepResult, PlanResult

# StepResult display
sr_ok = StepResult(step={"action": "forward", "seconds": 2.0}, ok=True, message="Moved: ...")
assert "✓" in sr_ok.display()
assert "2.0s" in sr_ok.display()

sr_fail = StepResult(step={"action": "stop"}, ok=False, message="Error: ...")
assert "✗" in sr_fail.display()

# PlanResult all_ok
pr = PlanResult()
pr.results.append(StepResult(step={}, ok=True, message="ok"))
assert pr.all_ok == True

pr.aborted = True
assert pr.all_ok == False
```

## Policy Factory Tests
```python
from agent import create_policy, NovaPolicy, MockPolicy, ReplayPolicy

# Mock policy
p = create_policy("mock")
assert isinstance(p, MockPolicy)
assert p.provider_name == "mock"

# Replay policy
lib = {"circle": {"_reasoning": "...", "pattern": "circle", "steps": [{"action": "stop"}]}}
p = create_policy("replay", library=lib)
assert isinstance(p, ReplayPolicy)
plan = p.plan("circle")
assert plan["pattern"] == "circle"

# Unknown provider
try:
    create_policy("unknown")
    assert False
except ValueError:
    pass
```

## DeepRacerTool Tests (requires no hardware)
```python
from agent import create_policy
from deepracer_agent_tool import DeepRacerTool, TaskStatus

tool = DeepRacerTool(policy=create_policy("mock"))
assert tool.tool_name == "deepracer"
assert tool._task_state.status == TaskStatus.IDLE

# Status action
status = tool._action_status()
assert status["status"] == "success"
assert "IDLE" in status["content"][0]["text"]

# Stop when idle
stop = tool._action_stop()
assert stop["status"] == "success"
assert "Nothing running" in stop["content"][0]["text"]

tool.cleanup()
```

## Running the Web UI for Manual Testing
```bash
cd phase-2-strands-robots-deepracer
python app_ui.py
# Open http://127.0.0.1:5000
```

Manual test checklist:
- [ ] Physics dashboard shows correct values
- [ ] Pattern list shows all 14 patterns
- [ ] Quick prompt buttons fill the instruction field
- [ ] POST /plan returns a plan with warnings array
- [ ] Execute button only enabled after plan is received
- [ ] SSE stream shows start → step × N → done events
- [ ] Stop button sends stopped event and halts stream
- [ ] Rotation warnings from /plan are displayed in UI
