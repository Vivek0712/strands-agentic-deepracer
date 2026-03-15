#!/usr/bin/env python3
"""
deepracer_agent_tool.py — DeepRacer as a Strands AgentTool.

Mirrors the strands-robots Robot class pattern exactly:
  execute  — blocking: plan + run full sequence, return when done
  start    — non-blocking: submit to background thread, return immediately
  status   — poll current task progress + pattern name
  stop     — abort running task + emergency hardware stop

Usage:
    from agent import create_policy
    from deepracer_agent_tool import DeepRacerTool
    from strands import Agent

    tool  = DeepRacerTool(policy=create_policy("nova"))
    agent = Agent(tools=[tool])
    agent("Drive a figure-8")
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from dotenv import load_dotenv
from strands.tools.tools import AgentTool
from strands.types._events import ToolResultEvent
from strands.types.tools import ToolSpec, ToolUse

from agent import (
    NavigationPolicy,
    PlanResult,
    StepResult,
    execute_step,
    execute_plan_full,
    validate_plan,
    MAX_STEP_SECONDS,
    MAX_PLAN_STEPS,
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
class DeepRacerTaskState:
    status:          TaskStatus            = TaskStatus.IDLE
    instruction:     str                   = ""
    pattern:         str                   = ""
    start_time:      float                 = 0.0
    duration:        float                 = 0.0
    completed_steps: int                   = 0
    total_steps:     int                   = 0
    error_message:   str                   = ""
    task_future:     Optional[Future]      = None
    result:          Optional[PlanResult]  = None


# ── AgentTool ─────────────────────────────────────────────────────────────────

class DeepRacerTool(AgentTool):
    """DeepRacer navigation as a Strands AgentTool."""

    def __init__(self, policy: NavigationPolicy, tool_name: str = "deepracer"):
        super().__init__()
        self._policy         = policy
        self._tool_name_str  = tool_name
        self._task_state     = DeepRacerTaskState()
        self._shutdown_event = threading.Event()
        self._executor       = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"{tool_name}_executor",
        )
        logger.info(
            f"DeepRacerTool '{tool_name}' ready "
            f"(policy: {policy.provider_name})"
        )

    # ── Identity ──────────────────────────────────────────────────────────────

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
                "Actions: execute (blocking), start (async), status, stop."
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
                                "Natural language instruction. Required for execute/start. "
                                "Examples: 'drive a figure-8', 'slalom 4 cones', "
                                "'spiral outward', 'parallel park'."
                            ),
                        },
                    },
                    "required": ["action"],
                }
            },
        }

    # ── Async execution core ──────────────────────────────────────────────────

    async def _execute_task_async(self, instruction: str) -> None:
        try:
            from deepracer_tools import deepracer_connect

            # Phase 1 — connect
            self._task_state.status        = TaskStatus.CONNECTING
            self._task_state.instruction   = instruction
            self._task_state.start_time    = time.time()
            self._task_state.error_message = ""

            connect_msg = await asyncio.to_thread(deepracer_connect)
            if is_error(connect_msg):
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = connect_msg
                return

            # Phase 2 — plan
            self._task_state.status = TaskStatus.PLANNING
            try:
                plan = await asyncio.to_thread(self._policy.plan, instruction)
                validate_plan(plan)
            except Exception as exc:
                self._task_state.status        = TaskStatus.ERROR
                self._task_state.error_message = f"Planning failed: {exc}"
                return

            steps = plan.get("steps", [])
            self._task_state.pattern     = plan.get("pattern", "unknown")
            self._task_state.total_steps = len(steps)
            self._task_state.status      = TaskStatus.RUNNING

            result = PlanResult(
                pattern   = plan.get("pattern",    "unknown"),
                reasoning = plan.get("_reasoning", ""),
            )

            # Phase 3 — execute
            for step in steps:
                if self._task_state.status != TaskStatus.RUNNING:
                    result.aborted      = True
                    result.abort_reason = "Stopped by user."
                    break
                if self._shutdown_event.is_set():
                    result.aborted      = True
                    result.abort_reason = "Tool shutdown."
                    break

                sr: StepResult = await asyncio.to_thread(execute_step, step)
                result.results.append(sr)
                self._task_state.completed_steps += 1

                if not sr.ok:
                    await asyncio.to_thread(deepracer_stop)
                    result.aborted      = True
                    result.abort_reason = sr.message
                    break

            self._task_state.duration = time.time() - self._task_state.start_time
            self._task_state.result   = result

            if self._task_state.status == TaskStatus.RUNNING:
                self._task_state.status = (
                    TaskStatus.STOPPED if result.aborted else TaskStatus.COMPLETED
                )

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] task exception: {exc}")
            self._task_state.status        = TaskStatus.ERROR
            self._task_state.error_message = str(exc)
            self._task_state.duration      = time.time() - self._task_state.start_time
            try:
                deepracer_stop()
            except Exception:
                pass

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
        s  = self._task_state
        ok = s.status == TaskStatus.COMPLETED

        lines = [
            f"{'✅' if ok else '❌'}  {s.status.value.upper()} — '{s.instruction}'",
            f"  Pattern  : {s.pattern}",
            f"  Steps    : {s.completed_steps}/{s.total_steps}",
            f"  Duration : {s.duration:.1f}s",
        ]
        if s.error_message:
            lines.append(f"  Error    : {s.error_message}")
        if s.result and s.result.results:
            lines.append("  Step log :")
            for sr in s.result.results:
                lines.append(f"  {sr.display()}")

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
                        f"❌ Already running: '{self._task_state.instruction}'\n"
                        "   Use action='stop' to abort first."
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
                    f"🚀 Started: '{instruction}'\n"
                    "   action='status' to poll · action='stop' to abort"
                )
            }],
        }

    def _action_status(self) -> Dict[str, Any]:
        s = self._task_state
        if s.status == TaskStatus.RUNNING:
            s.duration = time.time() - s.start_time

        lines = [f"📊 {s.status.value.upper()}"]
        if s.instruction:  lines.append(f"  Task    : {s.instruction}")
        if s.pattern:      lines.append(f"  Pattern : {s.pattern}")
        if s.total_steps:  lines.append(f"  Steps   : {s.completed_steps}/{s.total_steps}")
        if s.start_time:   lines.append(f"  Elapsed : {s.duration:.1f}s")
        if s.error_message:lines.append(f"  Error   : {s.error_message}")

        return {"status": "success", "content": [{"text": "\n".join(lines)}]}

    def _action_stop(self) -> Dict[str, Any]:
        if self._task_state.status not in (
            TaskStatus.RUNNING, TaskStatus.PLANNING, TaskStatus.CONNECTING
        ):
            return {
                "status": "success",
                "content": [{
                    "text": f"💤 Nothing running ({self._task_state.status.value})"
                }],
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
                    f"🛑 Stopped: '{self._task_state.instruction}'\n"
                    f"  Steps completed : {self._task_state.completed_steps}"
                    f"/{self._task_state.total_steps}\n"
                    f"  Elapsed         : {self._task_state.duration:.1f}s\n"
                    f"  Hardware        : {hw_msg}"
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
                    "content": [{"text": "❌ 'instruction' required for execute/start."}],
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
                    "content": [{"text": f"❌ Unknown action '{action}'."}],
                })
                return

            yield ToolResultEvent({"toolUseId": tid, **fn()})

        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] stream error: {exc}")
            yield ToolResultEvent({
                "toolUseId": tool_use.get("toolUseId", ""),
                "status": "error",
                "content": [{"text": f"❌ Tool error: {exc}"}],
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
            reset_client()
            logger.info(f"[{self._tool_name_str}] cleanup complete")
        except Exception as exc:
            logger.error(f"[{self._tool_name_str}] cleanup error: {exc}")

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass