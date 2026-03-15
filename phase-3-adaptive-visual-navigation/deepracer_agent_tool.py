#!/usr/bin/env python3
"""
deepracer_agent_tool.py — DeepRacerTool(AgentTool) with Phase 3 vision loop.

Mirrors strands-robots Robot class pattern:
  execute  — blocking plan + run, return when done
  start    — non-blocking async execution
  status   — poll progress
  stop     — abort + emergency hardware stop

Phase 3 addition: if the policy has `has_vision = True` (i.e. CameraPolicy),
the execution loop runs a Nova Pro vision assessment between every meaningful
step. Decisions:
  continue → execute step as planned
  replan   → call policy.plan() with new instruction, replace remaining steps
  abort    → emergency stop immediately

The vision loop is a transparent upgrade — if the policy does NOT have
has_vision, the loop runs identically to Phase 2.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from strands.tools.tools import AgentTool
from strands.types.tools import ToolSpec, ToolUse

# ToolResultEvent: try current and legacy SDK paths (strands.types layout varies by version)
try:
    from strands.types._events import ToolResultEvent
except ModuleNotFoundError:
    try:
        from strands.types.events import ToolResultEvent
    except ModuleNotFoundError:
        # Fallback when SDK has no _events submodule: wrap dict for ToolResultEvent({...})
        class ToolResultEvent(dict):
            """Minimal tool result event; used when strands.types._events is not available."""
            pass

from agent import (
    MAX_REPLANS,
    MAX_STEP_SECONDS,
    VISION_ASSESS_TIMEOUT,
    VISION_MIN_STEP_SECS,
    NavigationPolicy,
    PlanResult,
    StepResult,
    execute_step,
    execute_plan_full,
    validate_plan,
)
from deepracer_tools import deepracer_stop, reset_client, is_error

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)


# ── Task state ────────────────────────────────────────────────────────────────

class TaskStatus(Enum):
    IDLE       = "idle"
    CONNECTING = "connecting"
    PLANNING   = "planning"
    RUNNING    = "running"
    COMPLETED  = "completed"
    STOPPED    = "stopped"
    ERROR      = "error"


@dataclass
class VisionEvent:
    """A single vision assessment result logged in the task state."""
    step_index:      int
    action:          str    # "continue" | "replan" | "abort"
    reasoning:       str
    confidence:      float
    triggered_replan: bool = False


@dataclass
class DeepRacerTaskState:
    status:           TaskStatus           = TaskStatus.IDLE
    instruction:      str                  = ""
    pattern:          str                  = ""
    start_time:       float                = 0.0
    duration:         float                = 0.0
    completed_steps:  int                  = 0
    total_steps:      int                  = 0
    replan_count:     int                  = 0
    error_message:    str                  = ""
    task_future:      Optional[Future]     = None
    result:           Optional[PlanResult] = None
    vision_log:       List[VisionEvent]    = field(default_factory=list)


# ── AgentTool ─────────────────────────────────────────────────────────────────

class DeepRacerTool(AgentTool):
    """
    DeepRacer navigation as a Strands AgentTool.

    Pass event_callback to receive SSE-pushable events in real time.
    app_ui.py uses: event_callback=lambda event, data: _push(event, data)
    """

    def __init__(
        self,
        policy:         NavigationPolicy,
        tool_name:      str = "deepracer",
        event_callback: Optional[Any] = None,
    ) -> None:
        super().__init__()
        self._policy          = policy
        self._tool_name_str   = tool_name
        self._task_state      = DeepRacerTaskState()
        self._shutdown_event  = threading.Event()
        self._event_callback  = event_callback or (lambda event, data: None)

        # Single-worker executor — one plan runs at a time
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"{tool_name}_executor",
        )

        # Detect Phase 3 vision capability
        self._has_vision = (
            hasattr(policy, "has_vision") and policy.has_vision
        )

        logger.info(
            f"DeepRacerTool '{tool_name}' ready "
            f"(policy: {policy.provider_name}  vision: {self._has_vision})"
        )

    # ── AgentTool identity ────────────────────────────────────────────────────

    @property
    def tool_name(self) -> str:
        return self._tool_name_str

    @property
    def tool_type(self) -> str:
        return "deepracer"

    @property
    def tool_spec(self) -> ToolSpec:
        return {
            "name": self._tool_name_str,
            "description": (
                "Control an AWS DeepRacer car with natural language. "
                "Supports complex patterns: circle, figure-8, square, triangle, "
                "slalom, chicane, spiral-out, lane-change, parallel-park, and more. "
                + ("Phase 3 vision active: Nova Pro monitors each step. " if self._has_vision else "")
                + "Actions: execute (blocking), start (async), status, stop."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["execute", "start", "status", "stop"],
                            "default": "execute",
                            "description": (
                                "execute = blocking plan+run; "
                                "start = async plan+run; "
                                "status = poll; "
                                "stop = abort + emergency halt."
                            ),
                        },
                        "instruction": {
                            "type": "string",
                            "description": (
                                "Natural language driving instruction. "
                                "Required for execute/start. Examples: "
                                "'drive a figure-8', 'slalom through 4 cones', "
                                "'parallel park'."
                            ),
                        },
                    },
                    "required": ["action"],
                }
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _push(self, event: str, data: dict) -> None:
        """Emit an SSE-style event via the callback (app_ui.py or no-op)."""
        try:
            self._event_callback(event, data)
        except Exception as exc:
            logger.debug(f"event_callback error: {exc}")

    # ── Phase 2 / Phase 3 execution core ─────────────────────────────────────

    async def _execute_task_async(self, instruction: str) -> None:
        """
        Plan then execute in background — the heart of Phase 2 and Phase 3.

        Phase 2: simple step-by-step execution with stop_on_failure.
        Phase 3: same loop but with a vision assessment before each
                 meaningful step. Supports abort and replan decisions.
        """
        try:
            # ── Phase 1: connect ──────────────────────────────────────────────
            self._task_state.status        = TaskStatus.CONNECTING
            self._task_state.instruction   = instruction
            self._task_state.start_time    = time.time()
            self._task_state.error_message = ""
            self._task_state.vision_log    = []
            self._task_state.replan_count  = 0

            from deepracer_tools import deepracer_connect
            connect_msg = await asyncio.to_thread(deepracer_connect)
            if is_error(connect_msg):
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = connect_msg
                return

            # ── Phase 2: plan ─────────────────────────────────────────────────
            self._task_state.status = TaskStatus.PLANNING
            try:
                plan = await asyncio.to_thread(self._policy.plan, instruction)
                validate_plan(plan)
            except Exception as exc:
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = f"Planning failed: {exc}"
                return

            original_instruction = instruction
            remaining_steps      = list(plan.get("steps", []))
            self._task_state.pattern     = plan.get("pattern", "unknown")
            self._task_state.total_steps = len(remaining_steps)
            self._task_state.status      = TaskStatus.RUNNING

            result = PlanResult(
                pattern   = plan.get("pattern",    "unknown"),
                reasoning = plan.get("_reasoning", ""),
            )

            self._push("start", {
                "total":   self._task_state.total_steps,
                "pattern": self._task_state.pattern,
                "vision":  self._has_vision,
            })

            # ── Phase 3: execution loop with optional vision ───────────────────
            replan_count = 0

            while remaining_steps:
                # Check abort signals
                if self._task_state.status != TaskStatus.RUNNING:
                    result.aborted      = True
                    result.abort_reason = "Stopped by user."
                    break
                if self._shutdown_event.is_set():
                    result.aborted      = True
                    result.abort_reason = "Tool shutdown."
                    break

                step         = remaining_steps[0]
                action       = step.get("action", "")
                step_seconds = step.get("seconds")

                # ── Vision assessment (Phase 3 only) ──────────────────────────
                if self._has_vision and self._should_assess(action, step_seconds):
                    vision_result = await self._run_vision_check(
                        step             = step,
                        context_instruction = original_instruction,
                        step_index       = self._task_state.completed_steps + 1,
                        total_steps      = self._task_state.total_steps,
                        steps_remaining  = len(remaining_steps),
                        replan_count     = replan_count,
                        result           = result,
                    )

                    if vision_result == "abort":
                        result.aborted      = True
                        result.abort_reason = "Vision: immediate hazard detected."
                        break

                    if vision_result == "replan" and replan_count < MAX_REPLANS:
                        # remaining_steps was already replaced inside _run_vision_check
                        replan_count += 1
                        self._task_state.replan_count = replan_count
                        continue   # restart loop with new remaining_steps

                # ── Execute step ──────────────────────────────────────────────
                sr: StepResult = await asyncio.to_thread(execute_step, step)
                result.results.append(sr)
                self._task_state.completed_steps += 1
                remaining_steps.pop(0)   # advance plan

                self._push("step", {
                    "index":     self._task_state.completed_steps,
                    "action":    sr.step.get("action"),
                    "seconds":   sr.step.get("seconds"),
                    "ok":        sr.ok,
                    "message":   sr.message,
                    "emergency": sr.message.startswith("[emergency]"),
                })

                if not sr.ok:
                    await asyncio.to_thread(deepracer_stop)
                    result.aborted      = True
                    result.abort_reason = f"Step '{action}' failed: {sr.message}"
                    break

            # ── Finalize ──────────────────────────────────────────────────────
            self._task_state.duration = time.time() - self._task_state.start_time
            self._task_state.result   = result

            if self._task_state.status == TaskStatus.RUNNING:
                self._task_state.status = (
                    TaskStatus.STOPPED if result.aborted else TaskStatus.COMPLETED
                )

            if result.all_ok:
                self._push("done", {
                    "ok_count":    result.completed_steps,
                    "fail_count":  0,
                    "replan_count": replan_count,
                })
            else:
                self._push("done", {
                    "ok_count":    result.completed_steps,
                    "fail_count":  1,
                    "abort_reason": result.abort_reason,
                    "replan_count": replan_count,
                })

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] task exception: {exc}")
            self._task_state.status        = TaskStatus.ERROR
            self._task_state.error_message = str(exc)
            self._task_state.duration      = time.time() - self._task_state.start_time
            self._push("done", {"ok_count": 0, "fail_count": 1, "abort_reason": str(exc)})
            try:
                deepracer_stop()
            except Exception:
                pass

    def _should_assess(self, action: str, step_seconds: Any) -> bool:
        """Return True if this step warrants a vision assessment call."""
        if action in {"stop", "connect"}:
            return False
        if step_seconds is not None:
            try:
                if float(step_seconds) < VISION_MIN_STEP_SECS:
                    return False
            except (TypeError, ValueError):
                pass
        return True

    async def _run_vision_check(
        self,
        step: Dict[str, Any],
        context_instruction: str,
        step_index: int,
        total_steps: int,
        steps_remaining: int,
        replan_count: int,
        result: PlanResult,
    ) -> str:
        """
        Run one vision assessment and handle the decision.

        Returns:
            "continue" — proceed with step as planned (most common)
            "abort"    — stop the car immediately
            "replan"   — replace remaining_steps and return to loop (caller must handle)
        """
        # Import here to avoid circular imports at module level
        from vision_assessor import AssessContext, VisionDecision

        # Get latest camera frame
        frame = self._policy.camera_stream.get_latest_frame()
        if frame is None:
            logger.debug("[Vision] No frame available — skipping assessment.")
            return "continue"

        context = AssessContext(
            instruction     = context_instruction,
            step_index      = step_index,
            total_steps     = total_steps,
            current_action  = step.get("action", ""),
            current_seconds = float(step.get("seconds") or 2.0),
            steps_remaining = steps_remaining,
            replan_count    = replan_count,
        )

        # Call with timeout — never block execution for more than VISION_ASSESS_TIMEOUT
        try:
            decision: VisionDecision = await asyncio.wait_for(
                asyncio.to_thread(self._policy.assess_step, frame, context),
                timeout=VISION_ASSESS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"[Vision] assess() timed out after {VISION_ASSESS_TIMEOUT}s — continuing."
            )
            decision = VisionDecision(
                action="continue",
                reasoning=f"Timeout after {VISION_ASSESS_TIMEOUT}s",
                confidence=0.5,
            )

        # Log to task state
        vision_event = VisionEvent(
            step_index       = step_index,
            action           = decision.action,
            reasoning        = decision.reasoning,
            confidence       = decision.confidence,
            triggered_replan = decision.action == "replan",
        )
        self._task_state.vision_log.append(vision_event)

        # Push to UI
        self._push("vision", {
            "step":       step_index,
            "action":     decision.action,
            "reasoning":  decision.reasoning,
            "confidence": round(decision.confidence, 2),
        })

        logger.info(
            f"[Vision] step {step_index}: {decision.action}  "
            f"confidence={decision.confidence:.2f}  '{decision.reasoning}'"
        )

        # Handle decision
        if decision.action == "abort":
            await asyncio.to_thread(deepracer_stop)
            self._push("vision_abort", {"reasoning": decision.reasoning})
            return "abort"

        if decision.action == "replan" and replan_count < MAX_REPLANS:
            new_instruction = decision.new_instruction or context_instruction
            try:
                new_plan = await asyncio.to_thread(self._policy.plan, new_instruction)
                validate_plan(new_plan)
                new_steps = new_plan.get("steps", [])

                # Replace the remaining steps list in place so the caller sees changes
                # We can't return the new list directly (return val is a string),
                # so we store it temporarily and the caller re-reads via this object.
                # Actually simpler: store on self and let caller retrieve.
                self._pending_replan_steps = new_steps
                self._pending_replan_pattern = new_plan.get("pattern", "custom")

                self._task_state.total_steps = (
                    result.completed_steps + len(new_steps)
                )

                self._push("replan", {
                    "count":       replan_count + 1,
                    "instruction": new_instruction,
                    "new_steps":   len(new_steps),
                    "pattern":     self._pending_replan_pattern,
                })

                logger.info(
                    f"[Vision] Replan #{replan_count + 1}: "
                    f"'{new_instruction}' → {len(new_steps)} new steps  "
                    f"pattern={self._pending_replan_pattern}"
                )
                return "replan"

            except Exception as exc:
                logger.warning(
                    f"[Vision] Replan failed: {exc} — continuing with original plan."
                )
                return "continue"

        # "continue" or replan limit reached
        return "continue"

    # ── Execution loop shim ───────────────────────────────────────────────────
    # The vision check returns "replan" and stores new steps in
    # self._pending_replan_steps. The while loop in _execute_task_async
    # needs to read those. We handle this by overriding the remaining_steps
    # variable via a shared attribute rather than a return value.
    # The cleaner approach is to run the loop differently:

    async def _execute_task_async(self, instruction: str) -> None:  # noqa: F811
        """
        Plan then execute — Phase 2 compatible with optional Phase 3 vision loop.
        """
        try:
            self._task_state.status        = TaskStatus.CONNECTING
            self._task_state.instruction   = instruction
            self._task_state.start_time    = time.time()
            self._task_state.error_message = ""
            self._task_state.vision_log    = []
            self._task_state.replan_count  = 0

            from deepracer_tools import deepracer_connect
            connect_msg = await asyncio.to_thread(deepracer_connect)
            if is_error(connect_msg):
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = connect_msg
                return

            self._task_state.status = TaskStatus.PLANNING
            try:
                plan = await asyncio.to_thread(self._policy.plan, instruction)
                validate_plan(plan)
            except Exception as exc:
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = f"Planning failed: {exc}"
                return

            original_instruction = instruction
            remaining_steps      = list(plan.get("steps", []))
            self._task_state.pattern     = plan.get("pattern", "unknown")
            self._task_state.total_steps = len(remaining_steps)
            self._task_state.status      = TaskStatus.RUNNING
            replan_count = 0

            result = PlanResult(
                pattern   = plan.get("pattern",    "unknown"),
                reasoning = plan.get("_reasoning", ""),
            )

            self._push("start", {
                "total":   self._task_state.total_steps,
                "pattern": self._task_state.pattern,
                "vision":  self._has_vision,
            })

            # ── Main execution loop ───────────────────────────────────────────
            while remaining_steps:
                if self._task_state.status != TaskStatus.RUNNING:
                    result.aborted = True
                    result.abort_reason = "Stopped by user."
                    break
                if self._shutdown_event.is_set():
                    result.aborted = True
                    result.abort_reason = "Tool shutdown."
                    break

                step         = remaining_steps[0]
                action       = step.get("action", "")
                step_seconds = step.get("seconds")

                # ── Vision gate (Phase 3) ─────────────────────────────────────
                if self._has_vision and self._should_assess(action, step_seconds):
                    vision_outcome = await self._assess_and_decide(
                        step                = step,
                        original_instruction= original_instruction,
                        step_index          = self._task_state.completed_steps + 1,
                        total_steps         = self._task_state.total_steps,
                        steps_remaining     = len(remaining_steps),
                        replan_count        = replan_count,
                        result              = result,
                    )

                    if vision_outcome == "abort":
                        result.aborted      = True
                        result.abort_reason = "Vision: immediate hazard."
                        break

                    if vision_outcome == "replan":
                        # New steps are stored in self._pending_replan_steps
                        remaining_steps = list(getattr(self, "_pending_replan_steps", remaining_steps))
                        replan_count += 1
                        self._task_state.replan_count  = replan_count
                        self._task_state.total_steps   = result.completed_steps + len(remaining_steps)
                        continue

                # ── Execute this step ─────────────────────────────────────────
                sr: StepResult = await asyncio.to_thread(execute_step, step)
                result.results.append(sr)
                self._task_state.completed_steps += 1
                remaining_steps.pop(0)

                self._push("step", {
                    "index":     self._task_state.completed_steps,
                    "action":    sr.step.get("action"),
                    "seconds":   sr.step.get("seconds"),
                    "ok":        sr.ok,
                    "message":   sr.message,
                    "emergency": sr.message.startswith("[emergency]"),
                })

                if not sr.ok:
                    await asyncio.to_thread(deepracer_stop)
                    result.aborted      = True
                    result.abort_reason = f"Step '{action}' failed: {sr.message}"
                    break

            # ── Finalise ──────────────────────────────────────────────────────
            self._task_state.duration = time.time() - self._task_state.start_time
            self._task_state.result   = result

            if self._task_state.status == TaskStatus.RUNNING:
                self._task_state.status = (
                    TaskStatus.STOPPED if result.aborted else TaskStatus.COMPLETED
                )

            self._push("done", {
                "ok_count":    result.completed_steps,
                "fail_count":  int(not result.all_ok),
                "abort_reason": result.abort_reason,
                "replan_count": replan_count,
            })

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] task exception: {exc}")
            self._task_state.status        = TaskStatus.ERROR
            self._task_state.error_message = str(exc)
            self._task_state.duration      = time.time() - self._task_state.start_time
            self._push("done", {"ok_count": 0, "fail_count": 1, "abort_reason": str(exc)})
            try:
                deepracer_stop()
            except Exception:
                pass

    async def _execute_approved_plan(self, plan: Dict[str, Any]) -> None:
        """
        Execute an already-approved plan (from /plan). Used by the web UI when
        the user clicks Execute. No planning step — runs plan["steps"] with
        vision checks if enabled.
        """
        try:
            self._task_state.status        = TaskStatus.CONNECTING
            self._task_state.instruction  = plan.get("_instruction_hint", plan.get("pattern", ""))
            self._task_state.start_time    = time.time()
            self._task_state.error_message = ""
            self._task_state.vision_log   = []
            self._task_state.replan_count  = 0

            from deepracer_tools import deepracer_connect
            connect_msg = await asyncio.to_thread(deepracer_connect)
            if is_error(connect_msg):
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = connect_msg
                self._push("done", {"ok_count": 0, "fail_count": 1, "abort_reason": connect_msg})
                return

            original_instruction = plan.get("_instruction_hint", plan.get("pattern", ""))
            remaining_steps      = list(plan.get("steps", []))
            self._task_state.pattern     = plan.get("pattern", "unknown")
            self._task_state.total_steps = len(remaining_steps)
            self._task_state.status      = TaskStatus.RUNNING
            replan_count = 0

            result = PlanResult(
                pattern   = plan.get("pattern", "unknown"),
                reasoning = plan.get("_reasoning", ""),
            )

            self._push("start", {
                "total":   self._task_state.total_steps,
                "pattern": self._task_state.pattern,
                "vision":  self._has_vision,
            })

            while remaining_steps:
                if self._task_state.status != TaskStatus.RUNNING:
                    result.aborted = True
                    result.abort_reason = "Stopped by user."
                    break
                if self._shutdown_event.is_set():
                    result.aborted = True
                    result.abort_reason = "Tool shutdown."
                    break

                step         = remaining_steps[0]
                action       = step.get("action", "")
                step_seconds = step.get("seconds")

                if self._has_vision and self._should_assess(action, step_seconds):
                    vision_outcome = await self._assess_and_decide(
                        step                = step,
                        original_instruction= original_instruction,
                        step_index          = self._task_state.completed_steps + 1,
                        total_steps         = self._task_state.total_steps,
                        steps_remaining     = len(remaining_steps),
                        replan_count        = replan_count,
                        result              = result,
                    )
                    if vision_outcome == "abort":
                        result.aborted      = True
                        result.abort_reason = "Vision: immediate hazard."
                        break
                    if vision_outcome == "replan":
                        remaining_steps = list(getattr(self, "_pending_replan_steps", remaining_steps))
                        replan_count += 1
                        self._task_state.replan_count  = replan_count
                        self._task_state.total_steps   = result.completed_steps + len(remaining_steps)
                        continue

                sr: StepResult = await asyncio.to_thread(execute_step, step)
                result.results.append(sr)
                self._task_state.completed_steps += 1
                remaining_steps.pop(0)

                self._push("step", {
                    "index":     self._task_state.completed_steps,
                    "action":    sr.step.get("action"),
                    "seconds":   sr.step.get("seconds"),
                    "ok":        sr.ok,
                    "message":   sr.message,
                    "emergency": sr.message.startswith("[emergency]"),
                })

                if not sr.ok:
                    await asyncio.to_thread(deepracer_stop)
                    result.aborted      = True
                    result.abort_reason = f"Step '{action}' failed: {sr.message}"
                    break

            self._task_state.duration = time.time() - self._task_state.start_time
            self._task_state.result   = result
            if self._task_state.status == TaskStatus.RUNNING:
                self._task_state.status = (
                    TaskStatus.STOPPED if result.aborted else TaskStatus.COMPLETED
                )
            self._push("done", {
                "ok_count":    result.completed_steps,
                "fail_count":  int(not result.all_ok),
                "abort_reason": result.abort_reason,
                "replan_count": replan_count,
            })

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] _execute_approved_plan exception: {exc}")
            self._task_state.status        = TaskStatus.ERROR
            self._task_state.error_message = str(exc)
            self._task_state.duration      = time.time() - self._task_state.start_time
            self._push("done", {"ok_count": 0, "fail_count": 1, "abort_reason": str(exc)})
            try:
                deepracer_stop()
            except Exception:
                pass

    async def _assess_and_decide(
        self,
        step: Dict[str, Any],
        original_instruction: str,
        step_index: int,
        total_steps: int,
        steps_remaining: int,
        replan_count: int,
        result: PlanResult,
    ) -> str:
        """
        Run one Nova Pro vision assessment and return the outcome string:
        "continue" | "abort" | "replan"

        If the decision is "replan", stores the new step list in
        self._pending_replan_steps for the caller to consume.
        """
        from vision_assessor import AssessContext, VisionDecision

        frame = self._policy.camera_stream.get_latest_frame()
        if frame is None:
            return "continue"

        context = AssessContext(
            instruction     = original_instruction,
            step_index      = step_index,
            total_steps     = total_steps,
            current_action  = step.get("action", ""),
            current_seconds = float(step.get("seconds") or 2.0),
            steps_remaining = steps_remaining,
            replan_count    = replan_count,
        )

        try:
            decision: VisionDecision = await asyncio.wait_for(
                asyncio.to_thread(self._policy.assess_step, frame, context),
                timeout=VISION_ASSESS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            decision = VisionDecision(
                action    = "continue",
                reasoning = f"Timeout after {VISION_ASSESS_TIMEOUT}s",
                confidence= 0.5,
            )

        # Log + push
        self._task_state.vision_log.append(VisionEvent(
            step_index       = step_index,
            action           = decision.action,
            reasoning        = decision.reasoning,
            confidence       = decision.confidence,
            triggered_replan = (decision.action == "replan"),
        ))

        self._push("vision", {
            "step":       step_index,
            "action":     decision.action,
            "reasoning":  decision.reasoning,
            "confidence": round(decision.confidence, 2),
        })

        logger.info(
            f"[Vision] step {step_index}: {decision.action}  "
            f"conf={decision.confidence:.2f}  '{decision.reasoning}'"
        )

        if decision.action == "abort":
            await asyncio.to_thread(deepracer_stop)
            self._push("vision_abort", {"reasoning": decision.reasoning})
            return "abort"

        if decision.action == "replan" and replan_count < MAX_REPLANS:
            new_instruction = decision.new_instruction or original_instruction
            try:
                new_plan = await asyncio.to_thread(self._policy.plan, new_instruction)
                validate_plan(new_plan)
                self._pending_replan_steps = list(new_plan.get("steps", []))
                self._push("replan", {
                    "count":       replan_count + 1,
                    "instruction": new_instruction,
                    "new_steps":   len(self._pending_replan_steps),
                    "pattern":     new_plan.get("pattern", "custom"),
                })
                return "replan"
            except Exception as exc:
                logger.warning(f"[Vision] Replan failed: {exc} — continuing.")
                return "continue"

        return "continue"

    # ── Sync wrapper (mirrors strands-robots _execute_task_sync) ─────────────

    def _sync_wrapper(self, instruction: str) -> Dict[str, Any]:
        async def runner():
            await self._execute_task_async(instruction)

        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as ex:
                ex.submit(lambda: asyncio.run(runner())).result()
        except RuntimeError:
            asyncio.run(runner())

        return self._build_payload()

    def _build_payload(self) -> Dict[str, Any]:
        s   = self._task_state
        ok  = s.status == TaskStatus.COMPLETED

        lines = [
            f"{'OK' if ok else 'FAILED'} '{s.instruction}' — {s.status.value}",
            f"  Pattern      : {s.pattern}",
            f"  Steps        : {s.completed_steps}/{s.total_steps}",
            f"  Duration     : {s.duration:.1f}s",
        ]
        if self._has_vision:
            lines.append(f"  Replans      : {s.replan_count}")
            lines.append(f"  Vision checks: {len(s.vision_log)}")
        if s.error_message:
            lines.append(f"  Error        : {s.error_message}")
        if s.result and s.result.results:
            lines.append("  Step log:")
            for sr in s.result.results:
                lines.append(f"  {sr.display()}")
        if s.vision_log:
            lines.append("  Vision log:")
            for ve in s.vision_log:
                flag = " [REPLAN]" if ve.triggered_replan else ""
                lines.append(
                    f"    step {ve.step_index}: {ve.action} "
                    f"({ve.confidence:.0%}) — {ve.reasoning}{flag}"
                )

        return {
            "status":  "success" if ok else "error",
            "content": [{"text": "\n".join(lines)}],
        }

    # ── Action methods ────────────────────────────────────────────────────────

    def _action_execute(self, instruction: str) -> Dict[str, Any]:
        return self._sync_wrapper(instruction)

    def _action_start(self, instruction: str) -> Dict[str, Any]:
        if self._task_state.status == TaskStatus.RUNNING:
            return {
                "status": "error",
                "content": [{
                    "text": (
                        f"Already running: '{self._task_state.instruction}'. "
                        "Use action='stop' to abort first."
                    )
                }],
            }
        self._task_state = DeepRacerTaskState()
        self._task_state.task_future = self._executor.submit(
            self._sync_wrapper, instruction
        )
        return {
            "status": "success",
            "content": [{
                "text": (
                    f"Started: '{instruction}'\n"
                    + ("Vision monitoring active.\n" if self._has_vision else "")
                    + "Use action='status' to poll  ·  action='stop' to abort."
                )
            }],
        }

    def _action_status(self) -> Dict[str, Any]:
        s = self._task_state
        if s.status == TaskStatus.RUNNING:
            s.duration = time.time() - s.start_time

        lines = [f"{s.status.value.upper()}"]
        if s.instruction:
            lines.append(f"  Task    : {s.instruction}")
        if s.pattern:
            lines.append(f"  Pattern : {s.pattern}")
        if s.total_steps:
            lines.append(f"  Steps   : {s.completed_steps}/{s.total_steps}")
        if s.start_time:
            lines.append(f"  Elapsed : {s.duration:.1f}s")
        if self._has_vision and s.vision_log:
            lines.append(f"  Vision  : {len(s.vision_log)} checks  {s.replan_count} replans")
        if s.error_message:
            lines.append(f"  Error   : {s.error_message}")

        return {"status": "success", "content": [{"text": "\n".join(lines)}]}

    def _action_stop(self) -> Dict[str, Any]:
        if self._task_state.status not in (
            TaskStatus.RUNNING, TaskStatus.PLANNING, TaskStatus.CONNECTING
        ):
            return {
                "status": "success",
                "content": [{"text": f"Nothing running ({self._task_state.status.value})"}],
            }

        self._task_state.status = TaskStatus.STOPPED
        if self._task_state.task_future:
            self._task_state.task_future.cancel()

        hw_msg = ""
        try:
            hw_msg = deepracer_stop()
        except Exception as exc:
            hw_msg = f"stop_car raised: {exc}"

        return {
            "status": "success",
            "content": [{
                "text": (
                    f"Stopped: '{self._task_state.instruction}'\n"
                    f"  Steps: {self._task_state.completed_steps}/{self._task_state.total_steps}\n"
                    f"  Elapsed: {self._task_state.duration:.1f}s\n"
                    f"  Hardware: {hw_msg}"
                )
            }],
        }

    # ── Strands stream entry point ────────────────────────────────────────────

    async def stream(
        self,
        tool_use: ToolUse,
        invocation_state: Dict[str, Any],
        **kwargs: Any,
    ) -> AsyncGenerator[ToolResultEvent, None]:
        try:
            tid         = tool_use.get("toolUseId", "")
            inp         = tool_use.get("input", {})
            action      = inp.get("action", "execute")
            instruction = inp.get("instruction", "")

            if action in ("execute", "start") and not instruction:
                yield ToolResultEvent({
                    "toolUseId": tid, "status": "error",
                    "content": [{"text": "'instruction' required for execute/start."}],
                })
                return

            dispatch = {
                "execute": lambda: self._action_execute(instruction),
                "start":   lambda: self._action_start(instruction),
                "status":  self._action_status,
                "stop":    self._action_stop,
            }
            fn = dispatch.get(action)
            if fn is None:
                yield ToolResultEvent({
                    "toolUseId": tid, "status": "error",
                    "content": [{"text": f"Unknown action '{action}'."}],
                })
                return

            yield ToolResultEvent({"toolUseId": tid, **fn()})

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] stream error: {exc}")
            yield ToolResultEvent({
                "toolUseId": tool_use.get("toolUseId", ""),
                "status": "error",
                "content": [{"text": f"Tool error: {exc}"}],
            })

    # ── Resource cleanup ──────────────────────────────────────────────────────

    def cleanup(self) -> None:
        try:
            self._shutdown_event.set()
            if self._task_state.status in (
                TaskStatus.RUNNING, TaskStatus.PLANNING, TaskStatus.CONNECTING
            ):
                self._action_stop()
            self._executor.shutdown(wait=True, cancel_futures=True)

            # Stop camera stream if Phase 3 policy
            if self._has_vision and hasattr(self._policy, "cleanup"):
                self._policy.cleanup()

            reset_client()
            logger.info(f"[{self._tool_name_str}] cleanup complete")
        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] cleanup error: {exc}")

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass