#!/usr/bin/env python3
"""
app_ui.py — Phase 3: Closed-Loop Vision Navigation web UI.

Routes:
    GET  /              → dashboard (index.html)
    POST /plan          → LLM plan → JSON (stores instruction hint)
    POST /execute       → run approved plan with vision, stream via SSE
    POST /stop          → emergency stop
    GET  /stream        → SSE: start · step · vision · replan · done · stopped
    GET  /frame         → latest JPEG from camera (polled at 2 Hz by browser)
    GET  /vision_status → camera health JSON

Run:
    python app_ui.py
    open http://127.0.0.1:5000
"""

import asyncio
import base64
import json
import os
import queue
import threading
import warnings
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

from agent import (
    DEFAULT_MODEL,
    MAX_PLAN_STEPS,
    MAX_REPLANS,
    MAX_STEP_SECONDS,
    VISION_ASSESS_TIMEOUT,
    validate_plan,
)
from deepracer_tools import (
    PHYSICS_FWD_SPEED_MS,
    PHYSICS_MAX_CORNER_SPEED,
    PHYSICS_MIN_TURN_RADIUS_M,
    PHYSICS_TURN_SPEED_MS,
    deepracer_stop,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

app   = Flask(__name__)
MODEL = os.getenv("MODEL", DEFAULT_MODEL)

# ── SSE queue ─────────────────────────────────────────────────────────────────
# Thread-safe. Written by DeepRacerTool via _event_cb. Read by /stream.
_sse_queue: queue.Queue = queue.Queue()


def _push(event: str, data: dict) -> None:
    """Push one SSE message onto the queue."""
    _sse_queue.put(f"event: {event}\ndata: {json.dumps(data)}\n\n")


def _event_cb(event: str, data: dict) -> None:
    """Named callback passed to DeepRacerTool — avoids closure issues."""
    _push(event, data)


# Minimal 1×1 gray JPEG so /frame always returns image data (no 204)
_PLACEHOLDER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQACEQAD8AAn/9k="
)

# ── Phase 3 singletons ────────────────────────────────────────────────────────
_camera_policy  = None
_deepracer_tool = None
_current_plan   = None
_stop_flag      = threading.Event()
_init_error: Optional[str] = None  # Set if _init() fails; surfaced in /plan and /execute


def _init() -> None:
    """Create CameraPolicy + DeepRacerTool. Called once at startup."""
    global _camera_policy, _deepracer_tool, _init_error
    _init_error = None
    from camera_policy import create_camera_policy
    from deepracer_agent_tool import DeepRacerTool

    _camera_policy  = create_camera_policy()
    _deepracer_tool = DeepRacerTool(
        policy         = _camera_policy,
        tool_name      = "deepracer",
        event_callback = _event_cb,
    )
    print(f"  Phase 3 ready — policy: {_camera_policy.provider_name}")


try:
    _init()
except Exception as exc:
    _init_error = str(exc)
    print(f"  [app_ui] Init failed: {exc}")
    print("  Check DEEPRACER_IP, DEEPRACER_PASSWORD, VISION_MODEL, AWS credentials.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        model            = MODEL,
        vision_enabled   = True,
        min_turn_radius  = PHYSICS_MIN_TURN_RADIUS_M,
        max_corner_speed = PHYSICS_MAX_CORNER_SPEED,
        fwd_speed        = PHYSICS_FWD_SPEED_MS,
        turn_speed       = PHYSICS_TURN_SPEED_MS,
        max_step_secs    = MAX_STEP_SECONDS,
        max_plan_steps   = MAX_PLAN_STEPS,
        vision_model     = os.getenv("VISION_MODEL", "us.amazon.nova-pro-v1:0"),
        vision_timeout   = VISION_ASSESS_TIMEOUT,
        max_replans      = MAX_REPLANS,
        quick_prompts    = [
            "drive a full circle",
            "do a figure-8",
            "slalom through 3 cones",
            "drive a square",
            "drive a triangle",
            "drive a pentagon",
            "drive a hexagon",
            "spiral outward",
            "lane change to the right",
            "parallel park",
            "do a U-turn and come back",
            "drive an oval loop",
        ],
        patterns=[
            ("circle",        "360° rotation, tight or wide"),
            ("u-turn",        "Reverse heading"),
            ("figure-8",      "Two opposite circles"),
            ("square",        "4 sides, 90° corners"),
            ("triangle",      "3 sides, 120° corners"),
            ("pentagon",      "5 sides, 72° corners"),
            ("hexagon",       "6 sides, 60° corners"),
            ("oval",          "Straights + 180° ends"),
            ("slalom",        "Weave through N cones"),
            ("chicane",       "Single S-bend"),
            ("lane-change",   "Smooth lateral offset"),
            ("spiral-out",    "Expanding-radius loops"),
            ("zigzag",        "Sharp alternating turns"),
            ("parallel-park", "3-phase parking"),
        ],
    )


def _phase3_error_message() -> str:
    """Message to return when Phase 3 was not initialised (e.g. init failed at startup)."""
    if _init_error:
        return f"Phase 3 not initialised: {_init_error}"
    return (
        "Phase 3 not initialised. Check server logs and .env "
        "(DEEPRACER_IP, DEEPRACER_PASSWORD, AWS credentials)."
    )


@app.route("/plan", methods=["POST"])
def plan():
    global _current_plan
    if _camera_policy is None:
        return jsonify({"ok": False, "error": _phase3_error_message()}), 500

    body        = request.get_json(force=True)
    instruction = (body.get("instruction") or "").strip()
    if not instruction:
        return jsonify({"ok": False, "error": "No instruction provided."}), 400

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data = _camera_policy.plan(instruction)

        validate_plan(data)
        data["_instruction_hint"] = instruction
        _current_plan = data

        return jsonify({
            "ok":       True,
            "plan":     data,
            "warnings": [str(w.message) for w in caught],
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/execute", methods=["POST"])
def execute():
    if _current_plan is None:
        return jsonify({"ok": False, "error": "No plan. Get a plan first."}), 400
    if _deepracer_tool is None:
        return jsonify({"ok": False, "error": _phase3_error_message()}), 500

    # Drain any stale SSE events from a previous run
    while not _sse_queue.empty():
        try:
            _sse_queue.get_nowait()
        except queue.Empty:
            break

    _stop_flag.clear()

    plan = _current_plan

    def _worker():
        asyncio.run(_deepracer_tool._execute_approved_plan(plan))

    threading.Thread(target=_worker, daemon=True, name="phase3_exec").start()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop():
    _stop_flag.set()
    if _deepracer_tool is not None:
        try:
            _deepracer_tool._action_stop()
        except Exception:
            pass
    msg = ""
    try:
        msg = deepracer_stop()
    except Exception as exc:
        msg = str(exc)
    _push("stopped", {"message": f"Emergency stop. {msg}"})
    return jsonify({"ok": True, "message": msg})


@app.route("/stream")
def stream():
    """SSE endpoint. Browser keeps this open during execution.

    Blocks on _sse_queue.get() — yields each event the instant it arrives.
    Sends a heartbeat comment every 15 s to keep the connection alive.
    Closes after receiving 'done' or 'stopped' event.
    """
    def _generate():
        while True:
            try:
                msg = _sse_queue.get(timeout=15)
                yield msg
                if "event: done" in msg or "event: stopped" in msg:
                    break
            except queue.Empty:
                yield ": heartbeat\n\n"

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


@app.route("/frame")
def frame():
    """Latest JPEG from the camera. Always 200: real frame or placeholder when unavailable."""
    if _camera_policy is None:
        return Response(
            _PLACEHOLDER_JPEG,
            mimetype="image/jpeg",
            headers={"Cache-Control": "no-store", "X-Frame-Placeholder": "true"},
        )
    jpeg = _camera_policy.camera_stream.get_latest_frame()
    if not jpeg or len(jpeg) == 0:
        return Response(
            _PLACEHOLDER_JPEG,
            mimetype="image/jpeg",
            headers={"Cache-Control": "no-store", "X-Frame-Placeholder": "true"},
        )
    return Response(
        jpeg,
        mimetype="image/jpeg",
        headers={"Cache-Control": "no-store", "Content-Length": str(len(jpeg))},
    )


@app.route("/vision_status")
def vision_status():
    if _camera_policy is None:
        return jsonify({
            "enabled": False,
            "running": False,
            "error": "Camera not initialised. Check DEEPRACER_IP, DEEPRACER_PASSWORD, and AWS credentials.",
        })
    s = _camera_policy.camera_stream
    count, staleness = s.get_frame_info()
    err = s.get_error() if not s.is_running() else None
    if err is None and not s.is_running():
        err = "Stream not running. Click Reconnect to retry."
    return jsonify({
        "enabled":   True,
        "running":   s.is_running(),
        "frames":    count,
        "staleness": round(staleness, 1),
        "error":     err,
    })


@app.route("/reinit", methods=["POST"])
def reinit():
    """Retry Phase 3 initialization (e.g. after fixing .env). No restart required."""
    global _init_error
    try:
        _init()
        return jsonify({"ok": True, "message": "Phase 3 initialised."})
    except Exception as exc:
        _init_error = str(exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/camera/reconnect", methods=["POST"])
def camera_reconnect():
    """Restart the camera stream (e.g. after vehicle comes online)."""
    if _camera_policy is None:
        return jsonify({"ok": False, "error": "Camera not initialised. Try POST /reinit after fixing .env."}), 500
    stream = _camera_policy.camera_stream
    if stream.is_running():
        return jsonify({"ok": True, "message": "Camera stream already running."})
    ok = stream.start()
    return jsonify({
        "ok":      ok,
        "message": "Stream started with frames." if ok else "Stream started but no frames yet. Is the vehicle on and reachable?",
    })


# ── Cleanup ───────────────────────────────────────────────────────────────────

import atexit

@atexit.register
def _cleanup():
    if _camera_policy is not None:
        try:
            _camera_policy.cleanup()
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  DeepRacer — Phase 3: Closed-Loop Vision Navigation")
    print(f"  Planner : {MODEL}")
    print(f"  Vision  : {os.getenv('VISION_MODEL', 'us.amazon.nova-pro-v1:0')}")
    print(f"  http://127.0.0.1:5000\n")
    app.run(
        debug    = False,
        threaded = True,
        port     = int(os.getenv("PORT", "5000")),
    )