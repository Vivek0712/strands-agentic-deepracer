---
inclusion: manual
---

# Phase 3: Extending the Vision Pipeline

## Adding a New Vision Decision Action
The `VisionDecision.action` field currently supports "continue", "replan", "abort".
To add a new action (e.g. "slow"):
1. Add the new action string to `_parse_decision()` validation in `vision_assessor.py`
2. Add handling in `_assess_and_decide()` in `deepracer_agent_tool.py`
3. Add the new SSE event push in `_assess_and_decide()`
4. Update `_SYSTEM_PROMPT` in `vision_assessor.py` to describe the new action
5. Update `index.html` to display the new event type

## Changing the Vision Model
- Set `VISION_MODEL` in `.env` — no code changes needed
- Default: `us.amazon.nova-pro-v1:0` (cross-region inference profile)
- Any Bedrock model supporting multimodal Converse API works
- Changing the model may require adjusting `_SYSTEM_PROMPT` for different output formats

## Adjusting Vision Sensitivity
- `VISION_TIMEOUT` (default 4.0 s) — increase if Nova Pro calls are slow on your network
- `VISION_MIN_STEP` (default 0.5 s) — increase to skip vision on more short steps
- `MAX_REPLANS` (default 3) — increase to allow more adaptive replanning per run
- These are all `.env` variables — no code changes needed

## Adding a New Camera Source
`CameraStream._get_response()` handles three return types from `get_raw_video_stream()`:
- `requests.Response` with `iter_content` — used directly
- `str` URL — fetched with `requests.Session`
- `dict` with `url`/`stream_url`/`video_url` key — URL extracted then fetched

To add a new source type, extend `_get_response()` with the new case.

## Replacing CameraStream with a Different Frame Source
`DeepRacerTool` accesses frames via `self._policy.camera_stream.get_latest_frame()`.
Any object with `get_latest_frame() -> Optional[bytes]` works as a drop-in replacement.
The `CameraPolicy` constructor accepts any `CameraStream`-compatible object.

## Adding Vision to a Custom Policy
Any `NavigationPolicy` subclass can opt into vision by adding:
```python
@property
def has_vision(self) -> bool:
    return True

@property
def camera_stream(self):
    return self._camera_stream  # must have get_latest_frame()

def assess_step(self, frame_bytes, context) -> VisionDecision:
    return self._vision_assessor.assess(frame_bytes, context)
```
`DeepRacerTool` detects these via duck typing — no changes to the tool needed.

## Testing Vision Without Hardware
- `--mock` flag in `main.py` uses `MockPolicy` which has no `has_vision` — vision loop is skipped
- To test vision logic without a real camera, subclass `CameraStream` and override `get_latest_frame()` to return a test JPEG
- `VisionAssessor` can be tested independently with any JPEG bytes and an `AssessContext`
