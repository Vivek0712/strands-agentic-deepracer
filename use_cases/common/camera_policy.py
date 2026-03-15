#!/usr/bin/env python3
"""
camera_policy.py — Phase 3 CameraPolicy: NavigationPolicy with vision-in-the-loop.

Wraps three components:
    NovaPolicy       → initial LLM planning (same as Phase 2)
    VisionAssessor   → Nova Pro between-step safety checks
    CameraStream     → MJPEG frame buffer (always running in background)

The CameraPolicy implements the same NavigationPolicy interface as NovaPolicy
and MockPolicy, so it drops into the Phase 2 execution pipeline with zero
changes to validate_plan() or execute_step().

The additional vision capability is detected via the has_vision property:
    if hasattr(policy, 'has_vision') and policy.has_vision:
        decision = policy.assess_step(frame, context)

The execution loop with vision checking lives in deepracer_agent_tool.py's
_execute_task_async(), which was already built with a Phase 3 seam.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from agent import NavigationPolicy, NovaPolicy
from camera_stream import CameraStream
from vision_assessor import AssessContext, VisionAssessor, VisionDecision

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)


class CameraPolicy(NavigationPolicy):
    """
    NavigationPolicy with active camera vision.

    Owns a CameraStream (started on construction, stopped on cleanup)
    and a VisionAssessor (stateless Nova Pro wrapper).

    plan()        → delegates to the inner NovaPolicy (LLM text planning)
    assess_step() → calls VisionAssessor with latest frame + context
    has_vision    → True (allows deepracer_agent_tool to activate vision loop)
    """

    def __init__(
        self,
        nova_policy:      NovaPolicy,
        vision_assessor:  VisionAssessor,
        camera_stream:    CameraStream,
        max_replans:      int = 3,
        min_assess_secs:  float = 0.5,
        auto_start_camera: bool = True,
    ) -> None:
        """
        Args:
            nova_policy:       LLM planner for initial plans and replans.
            vision_assessor:   Nova Pro wrapper for frame assessment.
            camera_stream:     MJPEG frame buffer.
            max_replans:       Maximum vision-triggered replans per execution.
            min_assess_secs:   Skip vision check for steps shorter than this.
                               (0.3 s stabilisation steps are skipped at 0.5 s default)
            auto_start_camera: Start the CameraStream immediately on construction.
        """
        self._nova_policy     = nova_policy
        self._vision_assessor = vision_assessor
        self._camera_stream   = camera_stream
        self.max_replans      = max_replans
        self.min_assess_secs  = min_assess_secs

        if auto_start_camera:
            ok = self._camera_stream.start()
            if ok:
                logger.info("CameraPolicy: camera stream started and delivering frames.")
            else:
                logger.warning(
                    "CameraPolicy: camera stream started but no frames received yet. "
                    "Vision checks will be skipped until frames arrive."
                )

    # ── NavigationPolicy interface ────────────────────────────────────────────

    def plan(self, user_request: str) -> Dict[str, Any]:
        """Delegate planning to the inner NovaPolicy (LLM text planner).

        Vision is NOT used here — planning is still done by the text LLM.
        Vision is used between steps during execution.
        """
        return self._nova_policy.plan(user_request)

    @property
    def provider_name(self) -> str:
        return f"camera+{self._nova_policy.provider_name}"

    # ── Vision interface (checked by deepracer_agent_tool via duck typing) ─────

    @property
    def has_vision(self) -> bool:
        """Always True — signals the execution loop to activate vision checks."""
        return True

    @property
    def camera_stream(self) -> CameraStream:
        """Direct access to the camera stream for frame retrieval."""
        return self._camera_stream

    def assess_step(
        self,
        frame_bytes: bytes,
        context: AssessContext,
    ) -> VisionDecision:
        """
        Assess whether it is safe to execute the next plan step.

        Called by deepracer_agent_tool._execute_task_async() between steps
        when a frame is available and the step meets min_assess_secs.

        Args:
            frame_bytes: Latest JPEG from CameraStream.get_latest_frame().
            context:     Navigation context for the prompt.

        Returns:
            VisionDecision — never raises; any failure returns "continue".
        """
        return self._vision_assessor.assess(frame_bytes, context)

    # ── Resource management ───────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Stop the camera stream. Call on application exit."""
        self._camera_stream.stop()
        logger.info("CameraPolicy cleaned up.")


# ── Factory ───────────────────────────────────────────────────────────────────

def create_camera_policy(
    model:              Optional[str] = None,
    vision_model:       Optional[str] = None,
    region:             Optional[str] = None,
    max_replans:        Optional[int] = None,
    min_assess_secs:    Optional[float] = None,
    auto_start_camera:  bool = True,
) -> CameraPolicy:
    """
    Build a CameraPolicy from environment variables and optional overrides.

    All parameters fall back to environment variables:
        MODEL              → LLM planner model (Nova Lite default)
        VISION_MODEL       → Vision model (Nova Pro default)
        AWS_REGION         → Bedrock region
        MAX_REPLANS        → Max vision-triggered replans (default 3)
        VISION_MIN_STEP    → Min step duration for vision check (default 0.5 s)

    Usage:
        from camera_policy import create_camera_policy
        policy = create_camera_policy()
        # or with overrides:
        policy = create_camera_policy(max_replans=5, min_assess_secs=1.0)
    """
    nova_policy = NovaPolicy(model=model)

    vision_assessor = VisionAssessor(
        model_id=vision_model,
        region=region,
    )

    camera_stream = CameraStream()

    _max_replans     = max_replans     or int(os.getenv("MAX_REPLANS",     "3"))
    _min_assess_secs = min_assess_secs or float(os.getenv("VISION_MIN_STEP", "0.5"))

    return CameraPolicy(
        nova_policy      = nova_policy,
        vision_assessor  = vision_assessor,
        camera_stream    = camera_stream,
        max_replans      = _max_replans,
        min_assess_secs  = _min_assess_secs,
        auto_start_camera= auto_start_camera,
    )