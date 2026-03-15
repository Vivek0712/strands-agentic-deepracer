---
inclusion: always
---

# Phase 3: Adaptive Visual Navigation — Project Overview

## What This Is
A vision-augmented DeepRacer controller that combines the Phase 2 planning pipeline with
live camera feedback. The car streams MJPEG from its front camera into a background thread;
Nova Pro assesses each frame before a step executes and can continue, replan, or abort.

## Key Improvements Over Phase 2
- `CameraStream` — background daemon thread consuming MJPEG, always holds latest JPEG frame
- `VisionAssessor` — Nova Pro multimodal wrapper; returns `VisionDecision` (continue/replan/abort)
- `CameraPolicy` — `NavigationPolicy` that owns a `CameraStream` + `VisionAssessor`; planning still delegates to `NovaPolicy`
- `vision_assessor.py` — `AssessContext` + `VisionDecision` dataclasses; `VisionAssessor` class
- Vision loop in `_execute_task_async()` — `_should_assess()` gate, `_assess_and_decide()` with `asyncio.wait_for` timeout
- `--vision` flag in `main.py` — starts camera stream, uses `DeepRacerTool` for execution
- `/frame` route in `app_ui.py` — serves latest JPEG (or placeholder) polled at 2 Hz
- `/vision_status` route — camera health JSON
- `/reinit` and `/camera/reconnect` routes for recovery without restart
- `VISION_MODEL`, `MAX_REPLANS`, `VISION_ASSESS_TIMEOUT`, `VISION_MIN_STEP_SECS` env vars

## Key Files
| File | Purpose |
|---|---|
| `agent.py` | All Phase 2 + Phase 3 vision constants (VISION_ASSESS_TIMEOUT, MAX_REPLANS, VISION_MIN_STEP_SECS) |
| `deepracer_tools.py` | Identical to Phase 2 — no new @tool functions in Phase 3 |
| `deepracer_agent_tool.py` | DeepRacerTool extended with vision loop: `_should_assess()`, `_assess_and_decide()`, `_execute_approved_plan()` |
| `camera_stream.py` | Background MJPEG consumer; JPEG SOI/EOI marker extraction; `get_latest_frame()` non-blocking |
| `camera_policy.py` | `CameraPolicy(NavigationPolicy)` + `create_camera_policy()` factory |
| `vision_assessor.py` | `VisionAssessor`, `AssessContext`, `VisionDecision`; boto3 Converse API with raw JPEG bytes |
| `main.py` | Terminal REPL with `--vision` flag; `DeepRacerTool` used for vision execution |
| `app_ui.py` | Flask web UI with `/frame`, `/vision_status`, `/reinit`, `/camera/reconnect` |

## Architecture
```
User prompt
    │
    ▼
CameraPolicy.plan()
  └─ delegates to NovaPolicy (LLM text planning — same as Phase 2)
    │
    ▼
validate_plan() — same Phase 2 validation
    │
    ▼
User confirms (CLI y/N  or  Web Execute button)
    │
    ▼
DeepRacerTool._execute_task_async() / _execute_approved_plan()
  └─ for each step:
       _should_assess()? → VisionAssessor.assess(frame, context)
         continue → execute step
         replan   → policy.plan(new_instruction) → replace remaining steps
         abort    → deepracer_stop() immediately
  └─ stop_on_failure=True (hardware errors still trigger emergency stop)
    │
    ▼
aws-deepracer-control-v2 HTTP API → DeepRacer car
CameraStream (daemon thread) → MJPEG → latest JPEG frame in memory
```

## Environment Variables (.env)
| Variable | Default | Purpose |
|---|---|---|
| MODEL | us.amazon.nova-lite-v1:0 | Text planning model |
| VISION_MODEL | us.amazon.nova-pro-v1:0 | Vision model for frame assessment |
| DEEPRACER_IP | 192.168.0.3 | Car IP |
| DEEPRACER_PASSWORD | (required) | DeepRacer web console password |
| AWS_REGION | us-east-1 | Bedrock region |
| MAX_REPLANS | 3 | Max vision-triggered replans per execution |
| VISION_TIMEOUT | 4.0 | Seconds before vision assess() times out → "continue" |
| VISION_MIN_STEP | 0.5 | Steps shorter than this skip vision assessment |
| DEEPRACER_MAX_STEP_SECS | 5.0 | Hard cap per step |
| DEEPRACER_FWD_THROTTLE | 0.30 | Forward speed |
| DEEPRACER_TURN_THROTTLE | 0.20 | Turn speed |
| DEEPRACER_MAX_SPEED | 1.0 | Speed ceiling |
| DEEPRACER_STEER_ANGLE | 0.50 | Steering magnitude |

## Running
```bash
python main.py                          # Phase 2 mode (text planning only)
python main.py --vision                 # Phase 3: camera + Nova Pro vision
python main.py --mock                   # Offline, no Bedrock/hardware/camera
python main.py --model us.amazon.nova-pro-v1:0

python app_ui.py                        # Web UI at http://127.0.0.1:5000
```
