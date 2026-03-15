# Phase 1: Web UI — Requirements

## Overview
A minimal Flask web application that exposes the navigation planner through a browser interface. Users type a prompt, see a structured plan, then choose to execute or cancel — all without touching a terminal.

## Requirements

### REQ-UI-1: Flask Application
- MUST run on `host="0.0.0.0", port=5000, debug=False`
- MUST serve `templates/index.html` at `GET /`
- MUST serve static assets from `../assets/` at `/assets` URL path
- MUST use a single planner agent instance per process (singleton via `hasattr` caching)

### REQ-UI-2: Plan API (`POST /api/plan`)
- MUST accept `Content-Type: application/json` with `{"prompt": "..."}`
- MUST return 400 with `{"error": "prompt is required"}` if prompt is missing or empty
- MUST return `{"plan": { "steps": [...] }}` on success
- MUST return 500 with `{"error": "..."}` on agent/parse failure

### REQ-UI-3: Execute API (`POST /api/execute`)
- MUST accept `{"plan": { "steps": [...] }}`
- MUST return 400 with `{"error": "plan with steps is required"}` if plan is missing or empty
- MUST return `{"ok": true, "results": [...]}` on success
- Each result item MUST contain only: `step` (int), `action` (str), `seconds` (float|null), `ok` (bool)
- Raw tool output strings MUST NOT be included in the response
- MUST return 500 with `{"ok": false, "error": "..."}` on exception

### REQ-UI-4: Single-Page UI Layout
- MUST have a header with Strands logo, DeepRacer logo, and "Phase 1 · Planner" badge
- MUST have a two-column layout on desktop: chat panel (left) + plan panel (right)
- MUST collapse to single column on mobile (max-width: 768px)
- MUST have a dark theme with the DeepRacer background image at low opacity

### REQ-UI-5: Chat Panel
- MUST have a text input for the prompt
- MUST have a "Plan" button that triggers `POST /api/plan`
- MUST show a user chat bubble (right-aligned) with the submitted prompt
- MUST show an agent chat bubble (left-aligned) with a formatted plan summary
- MUST disable the Plan button during the fetch request

### REQ-UI-6: Plan Panel
- MUST be hidden until a plan is received
- MUST show a numbered ordered list of steps (action + seconds)
- MUST have an "Execute" button that triggers `POST /api/execute`
- MUST have a "Cancel" button that hides the panel and clears the current plan
- MUST disable the Execute button during execution

### REQ-UI-7: Result Feedback
- MUST show a result box with three visual states: loading (blue), success (green), error (red)
- MUST show "Planning…" status text while fetching a plan
- MUST show "Executing…" status text while executing
- MUST show step count on successful execution (e.g. "Done. 3 steps executed.")
- MUST show error message text on failure

### REQ-UI-8: Plan State Management
- Plan state MUST live in the browser (`currentPlan` JS variable)
- The server MUST NOT store pending plan state between requests
- Clicking Cancel MUST clear `currentPlan` and hide the plan panel
- A new Plan request MUST clear the previous plan and chat history
