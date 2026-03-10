#!/usr/bin/env python3
"""
Simple web UI for Phase 1 Agentic Navigation Planner.

Serves a minimal UI: prompt → plan → Execute / Cancel buttons → execution result.
No tool/thinking details. Run: python app_ui.py
"""

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from agent import create_planner, plan_navigation, execute_plan

BASE_DIR = Path(__file__).resolve().parent
# Assets live at strands-agentic-deepracer/assets/
ASSETS_DIR = BASE_DIR.parent / "assets"
app = Flask(
    __name__,
    template_folder=BASE_DIR / "templates",
    static_folder=ASSETS_DIR,
    static_url_path="/assets",
)


def get_planner():
    if not hasattr(get_planner, "_agent"):
        get_planner._agent = create_planner()
    return get_planner._agent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/plan", methods=["POST"])
def api_plan():
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    try:
        planner = get_planner()
        plan = plan_navigation(planner, prompt)
        return jsonify({"plan": plan})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/execute", methods=["POST"])
def api_execute():
    data = request.get_json() or {}
    plan = data.get("plan")
    if not plan or not plan.get("steps"):
        return jsonify({"error": "plan with steps is required"}), 400
    try:
        results = execute_plan(plan)
        # Minimal summary for UI: step index, action, ok (no long tool output)
        summary = [
            {
                "step": i,
                "action": s.get("action"),
                "seconds": s.get("seconds"),
                "ok": not (r and r.lower().startswith("error")),
            }
            for i, (s, r) in enumerate(results, 1)
        ]
        return jsonify({"ok": True, "results": summary})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
