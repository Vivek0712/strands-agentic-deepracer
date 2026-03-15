# Phase 1: Web UI — Implementation Tasks

## Task 1: Flask App Setup (`app_ui.py`)
- [ ] Define `BASE_DIR` and `ASSETS_DIR` using `Path(__file__).resolve().parent`
- [ ] Create Flask app with `template_folder=BASE_DIR/"templates"`, `static_folder=ASSETS_DIR`, `static_url_path="/assets"`
- [ ] Implement `get_planner()` with `hasattr(get_planner, "_agent")` singleton pattern
- [ ] Implement `GET /` returning `render_template("index.html")`
- [ ] Implement `POST /api/plan` with prompt validation and `plan_navigation()` call
- [ ] Implement `POST /api/execute` with plan validation and `execute_plan()` call
- [ ] Build minimal results summary (step, action, seconds, ok) — no raw tool strings
- [ ] Run with `app.run(host="0.0.0.0", port=5000, debug=False)`

## Task 2: HTML Structure (`templates/index.html`)
- [ ] `<html lang="en">` with UTF-8 charset and viewport meta
- [ ] Header: Strands logo + DeepRacer logo + title + Phase 1 badge
- [ ] Main card with `.chat-layout` grid (3fr / 2.3fr columns)
- [ ] Chat panel: label, prompt input, Plan button, `#chatHistory`, `#resultBox`, `#status`
- [ ] Plan panel `#planBox` (hidden by default): heading, `<ol #planSteps>`, Execute + Cancel buttons
- [ ] Footer with author name and GitHub/LinkedIn links
- [ ] Responsive: single column below 768px

## Task 3: CSS Styling
- [ ] Dark radial gradient background
- [ ] DeepRacer background image overlay at 18% opacity via `::before` pseudo-element
- [ ] `.card` with backdrop-filter blur and border
- [ ] `.btn-primary`, `.btn-success`, `.btn-outline` with hover transforms
- [ ] `.chat-bubble` with `.chat-user` (right-aligned) and `.chat-agent` (left-aligned) variants
- [ ] `.result-box` with `.loading`, `.success`, `.error`, `.hidden` states
- [ ] `button:disabled` opacity and cursor styles

## Task 4: JavaScript — Plan Flow
- [ ] Get DOM refs for all interactive elements on load
- [ ] `getPlanBtn` click handler: validate input, disable button, set status "Planning…"
- [ ] Fetch `POST /api/plan` with prompt JSON
- [ ] On success: set `currentPlan`, render `<li>` items in `#planSteps`, show `#planBox`
- [ ] Clear `#chatHistory`, add user bubble, add agent plan summary bubble
- [ ] On error: call `showResult(error, 'error')`
- [ ] Re-enable button in all cases

## Task 5: JavaScript — Execute Flow
- [ ] `executeBtn` click handler: guard `if (!currentPlan)`, disable button, set status "Executing…"
- [ ] Show loading result box
- [ ] Fetch `POST /api/execute` with `currentPlan`
- [ ] On success: show `"Done. N step(s) executed."` in success result box
- [ ] On error: show error message in error result box
- [ ] Re-enable button in all cases

## Task 6: JavaScript — Cancel Flow
- [ ] `cancelBtn` click handler: hide `#planBox`, set `currentPlan = null`, hide result box, clear status

## Task 7: JavaScript — Helpers
- [ ] `setStatus(msg)` — sets `#status` text
- [ ] `showResult(text, type)` — sets text and class on `#resultBox`, removes `hidden`
- [ ] `hideResult()` — adds `hidden` class to `#resultBox`
- [ ] `addChatBubble(text, who)` — creates `.chat-bubble` div, appends to `#chatHistory`, scrolls
- [ ] `formatPlanSummary(steps)` — returns `"1. forward 2s → 2. stop"` style string

## Task 8: Verification
- [ ] Confirm Plan button is disabled during fetch and re-enabled after
- [ ] Confirm Execute button is disabled during execution and re-enabled after
- [ ] Confirm Cancel clears plan state and hides panel
- [ ] Confirm result box shows correct colour for loading/success/error
- [ ] Confirm `/assets/strands-logo.png` and `/assets/deepracer-logo.png` load correctly
- [ ] Confirm mobile layout collapses to single column
