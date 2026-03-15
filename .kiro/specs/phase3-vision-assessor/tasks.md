# Phase 3 Vision Assessor — Tasks

## Task 1: Verify assess() never raises
- [ ] Returns safe_continue() on boto3 ClientError
- [ ] Returns safe_continue() on network timeout
- [ ] Returns safe_continue() on JSON parse failure
- [ ] Returns safe_continue() on any other exception
- [ ] safe_continue() has action="continue" and confidence=0.5

## Task 2: Verify Bedrock Converse API call format
- [ ] Image block uses raw bytes — NOT base64-encoded string
- [ ] Image block format: {"image": {"format": "jpeg", "source": {"bytes": frame_bytes}}}
- [ ] Image block comes BEFORE text block in content list
- [ ] system prompt passed as [{"text": _SYSTEM_PROMPT}]
- [ ] Response text extracted from response["output"]["message"]["content"][0]["text"]

## Task 3: Verify _parse_decision() robustness
- [ ] Strips ```json ... ``` fences before parsing
- [ ] Strips ``` ... ``` fences before parsing
- [ ] Unknown action defaults to "continue"
- [ ] confidence clamped to [0.0, 1.0]
- [ ] reasoning capped at 200 chars
- [ ] json.JSONDecodeError returns safe_continue("JSON parse failure.")

## Task 4: Verify VisionDecision fields
- [ ] action is one of "continue", "replan", "abort"
- [ ] new_instruction populated only when action=="replan"
- [ ] raw_response stored but not used in logic
- [ ] safe_continue() factory returns action="continue", confidence=0.5

## Task 5: Verify AssessContext fields
- [ ] step_index is 1-based (first step = 1)
- [ ] current_seconds is float (not None)
- [ ] replan_count starts at 0 and increments per replan

## Task 6: Verify boto3 client configuration
- [ ] connect_timeout=10
- [ ] read_timeout=30
- [ ] retries={"max_attempts": 1} — no automatic retries
- [ ] region from AWS_REGION env var, default "us-east-1"

## Task 7: Verify model defaults
- [ ] model_id defaults to VISION_MODEL env var
- [ ] Falls back to "us.amazon.nova-pro-v1:0" when VISION_MODEL not set
