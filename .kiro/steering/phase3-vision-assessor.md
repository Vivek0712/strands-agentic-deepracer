---
inclusion: fileMatch
fileMatchPattern: "phase-3-adaptive-visual-navigation/vision_assessor.py"
---

# Phase 3: vision_assessor.py — Steering

## Purpose
Nova Pro multimodal safety assessor. Takes raw JPEG bytes + navigation context,
calls Bedrock Converse API, returns a `VisionDecision`. Never raises to callers.

## Dataclasses

### AssessContext
Fields: `instruction`, `step_index` (1-based), `total_steps`, `current_action`,
`current_seconds`, `steps_remaining`, `replan_count`

### VisionDecision
Fields: `action` ("continue"|"replan"|"abort"), `reasoning` (≤200 chars),
`new_instruction` (populated only when action=="replan"), `confidence` (0.0–1.0),
`raw_response` (logged, not used in logic)

Factory: `VisionDecision.safe_continue(reason)` — returns action="continue", confidence=0.5

## Class: VisionAssessor

### Constructor
- `model_id` — defaults to `VISION_MODEL` env var, then `us.amazon.nova-pro-v1:0`
- `region` — defaults to `AWS_REGION` env var, then `us-east-1`
- boto3 client config: `connect_timeout=10`, `read_timeout=30`, `retries={"max_attempts": 1}`

### assess(frame_bytes, context) -> VisionDecision
- Calls `_call_nova()` inside a try/except — returns `safe_continue()` on ANY exception
- `frame_bytes` are raw JPEG bytes — passed directly as `source["bytes"]` in the image block
- NO base64 encoding — boto3 Converse API takes raw bytes

### Bedrock Converse API Call
```python
response = client.converse(
    modelId=model_id,
    system=[{"text": _SYSTEM_PROMPT}],
    messages=[{
        "role": "user",
        "content": [
            {"image": {"format": "jpeg", "source": {"bytes": frame_bytes}}},
            {"text": user_text}
        ]
    }],
    inferenceConfig={"maxTokens": 256, "temperature": 0.1},
)
raw_text = response["output"]["message"]["content"][0]["text"]
```

### _parse_decision(raw_text) -> VisionDecision
- Strips markdown fences (```json ... ```) before JSON parsing
- Validates `action` is one of "continue"/"replan"/"abort" — defaults to "continue" if unknown
- Clamps `confidence` to [0.0, 1.0]
- Caps `reasoning` at 200 chars
- Returns `safe_continue("JSON parse failure.")` on `json.JSONDecodeError`

## System Prompt Behaviour
- Biased toward "continue" — only "abort" on truly imminent collision (< 20 cm in frame)
- Respects original instruction: "stop when X" → abort; "avoid X" → replan; no mention → continue
- Blurry/dark/unclear frames → always "continue"
- Floor texture, lighting variations, minor drift → "continue"
