#!/usr/bin/env python3
"""
app_ui.py — Flask web UI for the Phase 2 Agentic Navigation Planner.

Routes:
    GET  /              → main dashboard (index.html)
    POST /plan          → call LLM planner, return plan JSON
    POST /execute       → run current plan, stream step results via SSE
    POST /stop          → emergency stop
    GET  /stream        → SSE endpoint polled by the browser

Run:
    python app_ui.py
    open http://127.0.0.1:5000
"""

import json
import os
import queue
import threading
import warnings
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from agent import (
    DEFAULT_MODEL,
    MAX_PLAN_STEPS,
    MAX_STEP_SECONDS,
    create_planner,
    execute_plan,
    plan_navigation,
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

_planner       = None
_current_plan  = None
_stop_flag     = threading.Event()
_sse_queue: "queue.Queue[str]" = queue.Queue()


def _get_planner():
    global _planner
    if _planner is None:
        _planner = create_planner(MODEL)
    return _planner


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _push(event: str, data: dict) -> None:
    _sse_queue.put(_sse(event, data))


@app.route("/")
def index():
    return render_template(
        "index.html",
        model=MODEL,
        min_turn_radius=PHYSICS_MIN_TURN_RADIUS_M,
        max_corner_speed=PHYSICS_MAX_CORNER_SPEED,
        fwd_speed=PHYSICS_FWD_SPEED_MS,
        turn_speed=PHYSICS_TURN_SPEED_MS,
        max_step_secs=MAX_STEP_SECONDS,
        max_plan_steps=MAX_PLAN_STEPS,
        quick_prompts=[
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
            ("u-turn",        "Reverse heading and continue"),
            ("figure-8",      "Two opposite circles"),
            ("square",        "4 sides, 90° corners"),
            ("triangle",      "3 sides, 120° corners"),
            ("pentagon",      "5 sides, 72° corners"),
            ("hexagon",       "6 sides, 60° corners"),
            ("oval",          "Straights + 180° ends"),
            ("slalom",        "Weave through N cones"),
            ("chicane",       "Single S-bend avoidance"),
            ("lane-change",   "Smooth lateral offset"),
            ("spiral-out",    "Expanding-radius loops"),
            ("zigzag",        "Sharp alternating turns"),
            ("parallel-park", "3-phase parking sequence"),
        ],
    )


@app.route("/plan", methods=["POST"])
def plan():
    global _current_plan
    body        = request.get_json(force=True)
    instruction = (body.get("instruction") or "").strip()
    if not instruction:
        return jsonify({"ok": False, "error": "No instruction provided."}), 400

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data = plan_navigation(_get_planner(), instruction)

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

    while not _sse_queue.empty():
        try:
            _sse_queue.get_nowait()
        except queue.Empty:
            break

    _stop_flag.clear()

    def _run():
        plan  = _current_plan
        steps = plan.get("steps", [])
        _push("start", {"total": len(steps), "pattern": plan.get("pattern", "—")})

        results = []
        aborted = False

        for idx, (step, message) in enumerate(execute_plan(plan, stop_on_failure=True)):
            if _stop_flag.is_set():
                _push("stopped", {"message": "Stopped by user."})
                aborted = True
                break

            action        = step.get("action", "?")
            seconds       = step.get("seconds")
            is_emergency  = message.startswith("[emergency]")
            ok            = not (
                message.lower().startswith("error") or is_emergency
            )

            results.append({"action": action, "ok": ok})
            _push("step", {
                "index":     idx + 1,
                "action":    action,
                "seconds":   seconds,
                "ok":        ok,
                "message":   message,
                "emergency": is_emergency,
            })

            if not ok and not is_emergency:
                aborted = True
                break

        if not aborted:
            _push("done", {
                "ok_count":   sum(1 for r in results if r["ok"]),
                "fail_count": sum(1 for r in results if not r["ok"]),
            })

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop():
    _stop_flag.set()
    msg = ""
    try:
        msg = deepracer_stop()
    except Exception as exc:
        msg = str(exc)
    _push("stopped", {"message": f"Emergency stop. {msg}"})
    return jsonify({"ok": True, "message": msg})


@app.route("/stream")
def stream():
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
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    print(f"\n🏎️  DeepRacer Phase 2 UI  —  model: {MODEL}")
    print("   http://127.0.0.1:5000\n")
    app.run(debug=True, threaded=True, port=5000)