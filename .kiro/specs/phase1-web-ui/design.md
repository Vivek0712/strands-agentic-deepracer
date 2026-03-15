# Phase 1: Web UI — Design

## Server Architecture

```
app_ui.py
│
├── BASE_DIR = Path(__file__).resolve().parent
├── ASSETS_DIR = BASE_DIR.parent / "assets"
│
├── Flask app
│   ├── template_folder = BASE_DIR / "templates"
│   ├── static_folder   = ASSETS_DIR
│   └── static_url_path = "/assets"
│
├── get_planner()          ← hasattr singleton, created once
│
├── GET  /                 → render_template("index.html")
├── POST /api/plan         → plan_navigation() → {"plan": {...}}
└── POST /api/execute      → execute_plan()   → {"ok": bool, "results": [...]}
```

## Request / Response Contracts

### POST /api/plan
```
Request:  { "prompt": "Move forward 2 seconds then stop" }
Response: { "plan": { "steps": [ {"action":"forward","seconds":2}, {"action":"stop"} ] } }
Error:    { "error": "prompt is required" }  HTTP 400
Error:    { "error": "<exception message>" } HTTP 500
```

### POST /api/execute
```
Request:  { "plan": { "steps": [...] } }
Response: { "ok": true, "results": [
              { "step": 1, "action": "forward", "seconds": 2.0, "ok": true },
              { "step": 2, "action": "stop",    "seconds": null, "ok": true }
           ]}
Error:    { "error": "plan with steps is required" }  HTTP 400
Error:    { "ok": false, "error": "<exception message>" } HTTP 500
```

## Frontend State Machine

```
IDLE
  │  user types prompt + clicks Plan
  ▼
PLANNING  (Plan button disabled, status="Planning…")
  │  /api/plan success
  ▼
PLAN_READY  (plan panel visible, Execute/Cancel enabled)
  │                    │
  │ click Execute       │ click Cancel
  ▼                    ▼
EXECUTING             IDLE
(Execute disabled,    (plan panel hidden,
 status="Executing…") currentPlan=null)
  │
  ▼
DONE  (result box shows success/error)
```

## UI Component Map

```
<body>
└── .app-shell
    ├── <header>
    │   ├── .brand (logos + title)
    │   └── .badge-phase "Phase 1 · Planner"
    │
    ├── <main class="card chat-layout">
    │   ├── .chat-card (left column)
    │   │   ├── <label> "Chat with your DeepRacer"
    │   │   ├── .prompt-row
    │   │   │   ├── <input #prompt>
    │   │   │   └── <button #getPlan>
    │   │   ├── #chatHistory  ← chat bubbles appended here
    │   │   ├── #resultBox    ← loading/success/error
    │   │   └── #status       ← "Planning…" / "Executing…"
    │   │
    │   └── .plan-box #planBox (right column, hidden until plan ready)
    │       ├── <h2> "Planned steps"
    │       ├── <ol #planSteps>  ← step list rendered here
    │       └── .plan-actions
    │           ├── <button #execute>
    │           └── <button #cancel>
    │
    └── <footer> (author + links)
```

## CSS Design Tokens
- Background: `radial-gradient(circle at top left, #1b4b9b 0, #040816 55%, #02030a 100%)`
- Card: `radial-gradient(circle at top left, rgba(49,95,181,0.4), rgba(5,10,30,0.95))`
- Primary button: `linear-gradient(135deg, #0d6efd, #38bdf8)`
- Success button: `linear-gradient(135deg, #16a34a, #4ade80)`
- Result loading: `rgba(37,99,235,0.16)` / text `#bfdbfe`
- Result success: `rgba(22,163,74,0.16)` / text `#bbf7d0`
- Result error: `rgba(220,38,38,0.16)` / text `#fecaca`

## JS Key Variables
- `currentPlan` — holds the plan dict between `/api/plan` and `/api/execute`; null when idle
- `chatHistory` — DOM element; cleared on each new Plan request
- `planBox` — shown/hidden via `style.display`
- `resultBox` — class toggled between `hidden`, `loading`, `success`, `error`
