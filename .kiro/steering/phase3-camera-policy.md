---
inclusion: fileMatch
fileMatchPattern: "phase-3-adaptive-visual-navigation/camera_policy.py"
---

# Phase 3: camera_policy.py — Steering

## Purpose
`CameraPolicy` is the Phase 3 `NavigationPolicy`. It owns a `CameraStream` and a
`VisionAssessor`. Planning delegates to the inner `NovaPolicy` (text LLM — unchanged
from Phase 2). Vision is used between steps during execution, not during planning.

## Class: CameraPolicy(NavigationPolicy)

### Constructor
```python
CameraPolicy(
    nova_policy:       NovaPolicy,
    vision_assessor:   VisionAssessor,
    camera_stream:     CameraStream,
    max_replans:       int   = 3,
    min_assess_secs:   float = 0.5,
    auto_start_camera: bool  = True,
)
```
- `auto_start_camera=True` calls `camera_stream.start()` immediately; logs warning if no frames yet
- `max_replans` and `min_assess_secs` are read by `DeepRacerTool` via duck typing

### NavigationPolicy Interface
- `plan(user_request) -> Dict` — delegates to `self._nova_policy.plan(user_request)`; vision NOT used here
- `provider_name` — returns `f"camera+{self._nova_policy.provider_name}"`

### Vision Interface (duck-typed by DeepRacerTool)
- `has_vision: bool` — always `True`; signals `DeepRacerTool` to activate vision loop
- `camera_stream: CameraStream` — direct access for `get_latest_frame()`
- `assess_step(frame_bytes, context) -> VisionDecision` — calls `self._vision_assessor.assess()`; never raises

### Resource Management
- `cleanup()` — calls `self._camera_stream.stop()`; registered with `atexit` in `app_ui.py`

## Factory: create_camera_policy()
```python
create_camera_policy(
    model=None,             # LLM planner model (falls back to MODEL env var)
    vision_model=None,      # Vision model (falls back to VISION_MODEL env var)
    region=None,            # AWS region (falls back to AWS_REGION env var)
    max_replans=None,       # Falls back to MAX_REPLANS env var (default 3)
    min_assess_secs=None,   # Falls back to VISION_MIN_STEP env var (default 0.5)
    auto_start_camera=True,
) -> CameraPolicy
```
- Creates `NovaPolicy`, `VisionAssessor`, `CameraStream` internally
- Used by both `main.py` (`--vision` flag) and `app_ui.py` (`_init()`)

## Key Design Decisions
- Planning is text-only (NovaPolicy) — vision is only used between execution steps
- `CameraPolicy` does NOT subclass `NovaPolicy` — it wraps it via composition
- `has_vision` is checked via `hasattr(policy, "has_vision") and policy.has_vision` in `DeepRacerTool`
- `assess_step()` is called by `DeepRacerTool._assess_and_decide()` — not by `CameraPolicy` itself
- `min_assess_secs` is stored on `CameraPolicy` but enforced by `DeepRacerTool._should_assess()`
