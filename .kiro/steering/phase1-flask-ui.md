---
inclusion: fileMatch
fileMatchPattern: "phase-1-agentic-navigation-planner/app_ui.py"
---

# Flask Web UI — Coding Standards & Patterns

## App Setup
- `Flask(__name__)` with `template_folder` pointing to `BASE_DIR / "templates"`
- Static assets served from `BASE_DIR.parent / "assets"` at `/assets` URL path
- Run on `host="0.0.0.0", port=5000, debug=False` — never enable debug in production

## Planner Singleton
Use the `get_planner()` function with `hasattr` caching pattern — one agent instance per process lifetime. Never recreate the agent per request.

## API Endpoints
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Serve `index.html` |
| `/api/plan` | POST | Accept `{"prompt": "..."}`, return `{"plan": {...}}` |
| `/api/execute` | POST | Accept `{"plan": {...}}`, return `{"ok": true, "results": [...]}` |

## Request Validation
- `/api/plan`: return 400 if `prompt` is missing or empty
- `/api/execute`: return 400 if `plan` is missing or has no `steps`
- All errors return `{"error": "..."}` JSON with appropriate HTTP status

## Execute Response Shape
Results array items must be minimal — only `step`, `action`, `seconds`, `ok` (bool). Never expose raw tool output strings to the UI.

## Error Detection
`ok` field per step: `not (r and r.lower().startswith("error"))` — keep this convention consistent.

## No State Between Requests
The Flask app is stateless beyond the planner singleton. Plans are passed back from the browser on execute — never store plan state server-side.
