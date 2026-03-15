---
inclusion: always
---

# Phase 3 — Safety Rules (Non-Negotiable)

All Phase 2 safety rules apply unchanged. These are the Phase 3 additions.

## Camera Safety
- Camera stream failures MUST NOT block or abort plan execution — camera is advisory only
- `CameraStream.get_latest_frame()` returns `None` when no frame is available — callers must handle None
- `_should_assess()` MUST return False when `action` is "stop" or "connect"
- `_should_assess()` MUST return False when `step_seconds < VISION_MIN_STEP_SECS` (default 0.5 s)
- A None frame from `get_latest_frame()` MUST cause `_assess_and_decide()` to return "continue" immediately — no API call

## Vision Assessment Safety
- `VisionAssessor.assess()` MUST catch ALL exceptions and return `VisionDecision.safe_continue()` — never raise to callers
- `asyncio.wait_for(..., timeout=VISION_ASSESS_TIMEOUT)` MUST wrap every `assess_step()` call — timeout returns "continue"
- Vision decisions are advisory: "abort" triggers `deepracer_stop()` then breaks the loop; "replan" replaces remaining steps
- `replan_count < MAX_REPLANS` MUST be checked before acting on a "replan" decision — at limit, treat as "continue"
- Every vision-triggered replan MUST call `validate_plan()` on the new plan — invalid plans fall back to "continue"

## Emergency Stop (inherited from Phase 2, extended)
- Vision "abort" decision MUST call `deepracer_stop()` before setting `result.aborted = True`
- Hardware step failure MUST still call `deepracer_stop()` even when vision is active
- `_action_stop()` in `DeepRacerTool` MUST call `deepracer_stop()` regardless of vision state
- `CameraPolicy.cleanup()` MUST call `camera_stream.stop()` — registered with `atexit` in `app_ui.py`

## Credentials (inherited from Phase 2)
- `DEEPRACER_PASSWORD` MUST never be logged, printed, or included in error messages
- Camera URL is derived from `DEEPRACER_IP` — never contains the password
- `.env` is gitignored — never commit real credentials

## is_error() Convention (inherited from Phase 2)
- `is_error()` in `deepracer_tools.py` is the SINGLE source of truth for error detection
- Phase 3 adds no new @tool functions — `deepracer_tools.py` is identical to Phase 2
