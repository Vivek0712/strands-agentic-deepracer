# Phase 3 Camera Policy — Tasks

## Task 1: Verify CameraPolicy.plan() delegates to NovaPolicy
- [ ] plan() calls self._nova_policy.plan(user_request)
- [ ] Vision is NOT used during planning
- [ ] Returns the plan dict from NovaPolicy unchanged

## Task 2: Verify has_vision property
- [ ] has_vision returns True
- [ ] DeepRacerTool detects it via hasattr(policy, "has_vision") and policy.has_vision
- [ ] Phase 2 policies (NovaPolicy, MockPolicy) have no has_vision attribute

## Task 3: Verify assess_step() never raises
- [ ] assess_step() calls self._vision_assessor.assess()
- [ ] VisionAssessor.assess() handles all exceptions internally
- [ ] assess_step() itself has no try/except needed — relies on VisionAssessor

## Task 4: Verify camera_stream property
- [ ] Returns self._camera_stream
- [ ] DeepRacerTool accesses it as self._policy.camera_stream.get_latest_frame()

## Task 5: Verify cleanup()
- [ ] Calls self._camera_stream.stop()
- [ ] Registered with atexit in app_ui.py
- [ ] Called in finally block in main.py

## Task 6: Verify auto_start_camera behaviour
- [ ] auto_start_camera=True calls camera_stream.start() in __init__
- [ ] Logs info when stream ready (start() returns True)
- [ ] Logs warning when no frames yet (start() returns False)
- [ ] auto_start_camera=False skips start() call

## Task 7: Verify create_camera_policy() factory
- [ ] Creates NovaPolicy(model=model) internally
- [ ] Creates VisionAssessor(model_id=vision_model, region=region) internally
- [ ] Creates CameraStream() internally
- [ ] max_replans falls back to int(os.getenv("MAX_REPLANS", "3"))
- [ ] min_assess_secs falls back to float(os.getenv("VISION_MIN_STEP", "0.5"))

## Task 8: Verify provider_name
- [ ] Returns f"camera+{self._nova_policy.provider_name}"
- [ ] e.g. "camera+us.amazon.nova-lite-v1:0"
