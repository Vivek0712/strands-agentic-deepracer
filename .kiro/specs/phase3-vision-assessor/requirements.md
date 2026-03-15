# Phase 3 Vision Assessor — Requirements

## Overview
`vision_assessor.py` provides Nova Pro multimodal safety assessment.
Takes raw JPEG bytes + navigation context, calls Bedrock Converse API,
returns a `VisionDecision`. Never raises to callers.

## Functional Requirements

### FR-1: AssessContext dataclass
Fields (all required):
- `instruction: str` — original user driving instruction
- `step_index: int` — 1-based position in the plan
- `total_steps: int` — total steps in current plan
- `current_action: str` — e.g. "forward", "left"
- `current_seconds: float` — duration of the step about to run
- `steps_remaining: int` — steps left including current
- `replan_count: int` — how many times replanned this run

### FR-2: VisionDecision dataclass
Fields:
- `action: str` — "continue" | "replan" | "abort"
- `reasoning: str` — model's explanation, capped at 200 chars
- `new_instruction: str` — populated only when action=="replan", else ""
- `confidence: float` — 0.0–1.0, clamped
- `raw_response: str` — logged only, not used in logic (repr=False)

Factory: `VisionDecision.safe_continue(reason="Defaulting to continue.") -> VisionDecision`
- Returns action="continue", confidence=0.5

### FR-3: VisionAssessor constructor
- `model_id` — defaults to `os.getenv("VISION_MODEL", "us.amazon.nova-pro-v1:0")`
- `region` — defaults to `os.getenv("AWS_REGION", "us-east-1")`
- `max_tokens=256`, `temperature=0.1`
- boto3 config: `connect_timeout=10`, `read_timeout=30`, `retries={"max_attempts": 1}`

### FR-4: VisionAssessor.assess(frame_bytes, context) -> VisionDecision
- Calls `_call_nova()` inside try/except
- Returns `VisionDecision.safe_continue(f"Assessment error: {exc}")` on ANY exception
- MUST NOT raise to callers

### FR-5: Bedrock Converse API call
```python
response = client.converse(
    modelId=self._model_id,
    system=[{"text": _SYSTEM_PROMPT}],
    messages=[{
        "role": "user",
        "content": [
            {"image": {"format": "jpeg", "source": {"bytes": frame_bytes}}},
            {"text": user_text}
        ]
    }],
    inferenceConfig={"maxTokens": self._max_tokens, "temperature": self._temperature},
)
raw_text = response["output"]["message"]["content"][0]["text"]
```
- `frame_bytes` are raw JPEG bytes — NO base64 encoding
- Image block comes BEFORE text block in content list

### FR-6: _parse_decision(raw_text) -> VisionDecision
- Strips markdown fences (```` ```json ... ``` ````) before JSON parsing
- Validates action is "continue"/"replan"/"abort" — defaults to "continue" if unknown
- Clamps confidence to [0.0, 1.0]
- Caps reasoning at 200 chars
- Returns `safe_continue("JSON parse failure.")` on `json.JSONDecodeError`

### FR-7: System prompt bias rules
- Default to "continue" — only "abort" on truly imminent collision (< 20 cm in frame)
- Respects original instruction: "stop when X" → abort; "avoid X" → replan; no mention → continue
- Blurry/dark/unclear frames → always "continue"
- Floor texture, lighting variations, minor drift → "continue"

## Non-Functional Requirements
- NFR-1: Thread-safe — boto3 clients are thread-safe; assess() can be called concurrently
- NFR-2: No retries — `max_attempts: 1`; timeout handled by `asyncio.wait_for` in caller
- NFR-3: `temperature=0.1` — low temperature for consistent JSON output
