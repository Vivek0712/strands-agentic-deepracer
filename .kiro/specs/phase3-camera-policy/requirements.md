# Phase 3 Camera Policy — Requirements

## Overview
`camera_policy.py` provides `CameraPolicy` — the Phase 3 `NavigationPolicy`.
It owns a `CameraStream` and `VisionAssessor`. Planning delegates to `NovaPolicy`.
Vision is used between execution steps, not during planning.

## Functional Requirements

### FR-1: CameraPolicy constructor
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
- `auto_start_camera=True` calls `camera_stream.start()` in `__init__`
- Logs info if stream ready, warning if no frames yet
- `max_replans` and `min_assess_secs` stored as attributes (read by DeepRacerTool)

### FR-2: CameraPolicy.plan(user_request) -> Dict
- Delegates entirely to `self._nova_policy.plan(user_request)`
- Vision NOT used during planning
- Returns validated plan dict (validation done inside NovaPolicy)

### FR-3: CameraPolicy.provider_name -> str
- Returns `f"camera+{self._nova_policy.provider_name}"`

### FR-4: CameraPolicy.has_vision -> bool
- Always returns `True`
- Signals `DeepRacerTool` to activate vision loop via duck typing

### FR-5: CameraPolicy.camera_stream -> CameraStream
- Property returning `self._camera_stream`
- Used by `DeepRacerTool._assess_and_decide()` to call `get_latest_frame()`

### FR-6: CameraPolicy.assess_step(frame_bytes, context) -> VisionDecision
- Calls `self._vision_assessor.assess(frame_bytes, context)`
- Never raises — `VisionAssessor.assess()` handles all exceptions internally

### FR-7: CameraPolicy.cleanup()
- Calls `self._camera_stream.stop()`
- Called by `atexit` in `app_ui.py` and `finally` in `main.py`

### FR-8: create_camera_policy() factory
```python
create_camera_policy(
    model=None,             # LLM model, falls back to MODEL env var
    vision_model=None,      # Vision model, falls back to VISION_MODEL env var
    region=None,            # AWS region, falls back to AWS_REGION env var
    max_replans=None,       # Falls back to int(MAX_REPLANS env var, default 3)
    min_assess_secs=None,   # Falls back to float(VISION_MIN_STEP env var, default 0.5)
    auto_start_camera=True,
) -> CameraPolicy
```
- Creates `NovaPolicy(model=model)` internally
- Creates `VisionAssessor(model_id=vision_model, region=region)` internally
- Creates `CameraStream()` internally
- Used by `main.py --vision` and `app_ui.py _init()`

## Non-Functional Requirements
- NFR-1: `CameraPolicy` wraps `NovaPolicy` via composition — does NOT subclass it
- NFR-2: `has_vision` checked via `hasattr(policy, "has_vision") and policy.has_vision` in DeepRacerTool
- NFR-3: `assess_step()` called by `DeepRacerTool._assess_and_decide()` — not by CameraPolicy itself
- NFR-4: `min_assess_secs` stored on CameraPolicy but enforced by `DeepRacerTool._should_assess()`
