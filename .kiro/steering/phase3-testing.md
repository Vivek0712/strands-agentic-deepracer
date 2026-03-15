---
inclusion: manual
---

# Phase 3: Testing Guide

## Running Without Hardware (--mock)
```bash
cd phase-3-adaptive-visual-navigation
python main.py --mock
```
- Uses `MockPolicy` — no Bedrock, no hardware, no camera
- Vision loop is NOT active (MockPolicy has no `has_vision`)
- Good for testing the REPL flow and plan display

## Running Phase 2 Mode (text planning, no vision)
```bash
python main.py
```
- Uses `NovaPolicy` — requires Bedrock credentials
- No camera stream started
- Identical to Phase 2 execution

## Running Phase 3 Mode (full vision)
```bash
python main.py --vision
```
- Requires: DEEPRACER_IP, DEEPRACER_PASSWORD, AWS credentials, VISION_MODEL access
- Starts `CameraStream` — waits up to 15 s for first frame
- Vision checks run between each step ≥ 0.5 s

## Testing VisionAssessor in Isolation
```python
from vision_assessor import VisionAssessor, AssessContext

assessor = VisionAssessor()  # uses VISION_MODEL env var
with open("test_frame.jpg", "rb") as f:
    frame = f.read()

ctx = AssessContext(
    instruction="drive a square",
    step_index=1, total_steps=9,
    current_action="forward", current_seconds=2.0,
    steps_remaining=9, replan_count=0,
)
decision = assessor.assess(frame, ctx)
print(decision.action, decision.confidence, decision.reasoning)
```

## Testing CameraStream in Isolation
```python
from camera_stream import CameraStream

stream = CameraStream()
ok = stream.start()          # blocks up to 15 s
print("Stream ready:", ok)
frame = stream.get_latest_frame()
print("Frame size:", len(frame) if frame else "None")
stream.stop()
```

## Checking Vision Status (Web UI)
```bash
curl http://127.0.0.1:5000/vision_status
# {"enabled": true, "running": true, "frames": 42, "staleness": 0.1, "error": null}
```

## Reconnecting Camera After Vehicle Restart
```bash
curl -X POST http://127.0.0.1:5000/camera/reconnect
```

## Reinitialising After .env Fix
```bash
curl -X POST http://127.0.0.1:5000/reinit
```

## Key Things to Verify
- `VisionDecision.safe_continue()` returned on any assess() exception — never raises
- `asyncio.wait_for` timeout returns "continue" — never blocks execution
- None frame from `get_latest_frame()` → "continue" immediately (no API call)
- Vision "abort" calls `deepracer_stop()` before breaking the loop
- Replan count checked against `MAX_REPLANS` before acting on "replan"
- `validate_plan()` called on every vision-triggered replan
- `CameraPolicy.cleanup()` called on exit (atexit in app_ui.py, finally in main.py)
