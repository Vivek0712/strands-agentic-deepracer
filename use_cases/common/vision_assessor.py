#!/usr/bin/env python3
"""
vision_assessor.py — Nova Pro multimodal vision safety assessor for Phase 3.

Takes a JPEG frame (raw bytes) + navigation context and asks Nova Pro one
question: is it safe to proceed with the current plan step?

Returns a VisionDecision with one of three actions:
    "continue"  — path looks clear; execute the next step as planned
    "replan"    — visible scene change warrants a revised instruction
    "abort"     — immediate hazard; stop the car now

API notes (confirmed from AWS docs):
    - Use boto3 Converse API: client.converse(...)
    - Image is passed as raw bytes in source["bytes"] — NO base64 encoding
    - Supported format: "jpeg" | "png" | "gif" | "webp"
    - Model ID: us.amazon.nova-pro-v1:0  (cross-region inference profile)
    - Response text: response["output"]["message"]["content"][0]["text"]
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_VISION_MODEL = "us.amazon.nova-pro-v1:0"

# System prompt — tells Nova Pro its role and output format
_SYSTEM_PROMPT = """You are a real-time navigation safety monitor for an AWS DeepRacer autonomous car.
You receive a JPEG frame from the car's front camera and the current navigation context.

Your ONLY job: decide if it is safe to proceed with the next planned movement step,
based on what you see AND what the user's original instruction says to do.

Output format — respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{
  "action": "continue" | "replan" | "abort",
  "reasoning": "<max 25 words explaining your decision>",
  "new_instruction": "<revised driving instruction if action=replan, else empty string>",
  "confidence": <float 0.0-1.0>
}

Decision rules:
  continue — path ahead is clear; proceed as planned
  replan   — scene has changed and a different route would help; provide new_instruction
  abort    — stop the car immediately

CRITICAL — read the user's original instruction and honour it:
  - Instruction contains "stop when" / "stop if" / "halt" + obstacle →
    use "abort" when that condition is visible. Do NOT replan.
  - Instruction contains "avoid" / "go around" / "navigate around" →
    use "replan" with a suggested alternative route.
  - Instruction makes no mention of obstacles →
    default to "continue" unless a collision is truly imminent (< 20 cm in frame).

General bias rules:
  1. Normal floor texture, lighting variations, minor positional drift → "continue".
  2. Tape or markings on the floor only matter if the instruction references them.
  3. Blurry, dark, or unclear frame → always "continue".
  4. Distant walls or track boundaries outside the immediate path → "continue".
  5. When action is "abort", leave new_instruction as an empty string.
"""

# User message template
_USER_PROMPT_TEMPLATE = """Navigation context:
  Original instruction : {instruction}
  Next step            : {action}{seconds_str}
  Plan progress        : step {step_index} of {total_steps}
  Steps remaining      : {steps_remaining}
  Times replanned      : {replan_count}

Look at the camera frame and decide: continue, replan, or abort?

Key reminder: honour the original instruction.
  - If it says stop on obstacles → "abort" when you see one.
  - If it says avoid / go around → "replan" with a new route.
  - If it says nothing about obstacles → "continue" unless collision is imminent.
"""


# ── Data types ─────────────────────────────────────────────────────────────────

@dataclass
class AssessContext:
    """Context passed to VisionAssessor.assess() describing the current plan state."""
    instruction:     str
    step_index:      int    # 1-based position in the plan
    total_steps:     int
    current_action:  str    # e.g. "forward", "left"
    current_seconds: float  # duration of the step about to run
    steps_remaining: int    # steps left including current
    replan_count:    int    # how many times we've already replanned this run


@dataclass
class VisionDecision:
    """Parsed result of a single Nova Pro vision assessment."""
    action:          str            # "continue" | "replan" | "abort"
    reasoning:       str            # model's brief explanation (not executed)
    new_instruction: str = ""       # populated only when action == "replan"
    confidence:      float = 1.0    # model self-assessment 0.0–1.0
    raw_response:    str = field(default="", repr=False)  # logged, not used

    @classmethod
    def safe_continue(cls, reason: str = "Defaulting to continue.") -> "VisionDecision":
        """Factory for a safe fallback when assessment fails or times out."""
        return cls(action="continue", reasoning=reason, confidence=0.5)


# ── Assessor ──────────────────────────────────────────────────────────────────

class VisionAssessor:
    """
    Wraps a single boto3 Converse API call to Nova Pro with an image + context.

    Thread-safe: boto3 clients are thread-safe; multiple threads can call
    assess() concurrently (though in Phase 3 we only call it from one
    async thread at a time).
    """

    def __init__(
        self,
        model_id:    Optional[str]   = None,
        region:      Optional[str]   = None,
        max_tokens:  int             = 256,
        temperature: float           = 0.1,
    ) -> None:
        self._model_id   = model_id or os.getenv("VISION_MODEL", DEFAULT_VISION_MODEL)
        self._max_tokens = max_tokens
        self._temperature = temperature

        region = region or os.getenv("AWS_REGION", "us-east-1")

        # Use a generous timeout — Nova Pro vision calls can take 2–4 s
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                connect_timeout=10,
                read_timeout=30,
                retries={"max_attempts": 1},  # no retries — we have our own timeout
            ),
        )
        logger.info(
            f"VisionAssessor ready: model={self._model_id} region={region}"
        )

    # ── Public method ─────────────────────────────────────────────────────────

    def assess(self, frame_bytes: bytes, context: AssessContext) -> VisionDecision:
        """
        Send a JPEG frame + navigation context to Nova Pro and parse the decision.

        Args:
            frame_bytes: Raw JPEG bytes from CameraStream.get_latest_frame().
                         Passed directly as source["bytes"] — no base64 needed
                         with the boto3 Converse API.
            context:     Current plan state for the prompt.

        Returns:
            VisionDecision. On any error (network, parse failure, unexpected
            response) returns VisionDecision.safe_continue() so the car never
            stalls waiting for a cloud API.
        """
        try:
            return self._call_nova(frame_bytes, context)
        except Exception as exc:
            logger.warning(
                f"[VisionAssessor] assess() failed: {exc}. "
                "Returning safe 'continue'."
            )
            return VisionDecision.safe_continue(f"Assessment error: {exc}")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_user_text(self, context: AssessContext) -> str:
        seconds_str = (
            f" for {context.current_seconds:.1f}s"
            if context.current_seconds > 0
            else ""
        )
        return _USER_PROMPT_TEMPLATE.format(
            instruction    = context.instruction,
            action         = context.current_action,
            seconds_str    = seconds_str,
            step_index     = context.step_index,
            total_steps    = context.total_steps,
            steps_remaining= context.steps_remaining,
            replan_count   = context.replan_count,
        )

    def _call_nova(self, frame_bytes: bytes, context: AssessContext) -> VisionDecision:
        """Make the actual Converse API call and parse the response."""
        user_text = self._build_user_text(context)

        # Image block: raw bytes, format "jpeg"
        # CRITICAL: boto3 Converse API takes raw bytes — NOT base64-encoded strings
        image_block = {
            "image": {
                "format": "jpeg",
                "source": {
                    "bytes": frame_bytes,   # raw JPEG bytes, no encoding needed
                },
            }
        }
        text_block = {"text": user_text}

        logger.debug(
            f"[VisionAssessor] Calling Nova Pro — "
            f"frame={len(frame_bytes)}B  step={context.step_index}/{context.total_steps}  "
            f"action={context.current_action}"
        )

        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": _SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [image_block, text_block],
                }
            ],
            inferenceConfig={
                "maxTokens":   self._max_tokens,
                "temperature": self._temperature,
            },
        )

        # Response path: response["output"]["message"]["content"][0]["text"]
        raw_text = response["output"]["message"]["content"][0]["text"]

        logger.debug(
            f"[VisionAssessor] Raw response: {raw_text!r}  "
            f"tokens_in={response['usage']['inputTokens']}  "
            f"tokens_out={response['usage']['outputTokens']}"
        )

        return self._parse_decision(raw_text)

    @staticmethod
    def _parse_decision(raw_text: str) -> VisionDecision:
        """
        Parse Nova Pro's JSON response into a VisionDecision.

        Handles markdown fences (```json ... ```) that models sometimes emit
        despite being told not to. Falls back to safe_continue() on any error.
        """
        text = raw_text.strip()

        # Strip ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$",          "", text).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning(
                f"[VisionAssessor] JSON parse failed ({exc}). "
                f"Raw: {raw_text!r}. Returning 'continue'."
            )
            return VisionDecision.safe_continue("JSON parse failure.")

        # Validate action field
        action = str(data.get("action", "continue")).lower().strip()
        if action not in {"continue", "replan", "abort"}:
            logger.warning(
                f"[VisionAssessor] Unknown action '{action}'. Defaulting to 'continue'."
            )
            action = "continue"

        # Parse confidence — clamp to [0.0, 1.0]
        try:
            confidence = float(data.get("confidence", 1.0))
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5

        decision = VisionDecision(
            action          = action,
            reasoning       = str(data.get("reasoning", ""))[:200],  # cap length
            new_instruction = str(data.get("new_instruction", "")),
            confidence      = confidence,
            raw_response    = raw_text,
        )

        logger.info(
            f"[VisionAssessor] decision={decision.action}  "
            f"confidence={decision.confidence:.2f}  "
            f"reasoning={decision.reasoning!r}"
        )

        return decision
