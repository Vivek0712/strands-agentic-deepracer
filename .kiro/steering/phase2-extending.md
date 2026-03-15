---
inclusion: manual
---

# Phase 2: Extension Guide

## Adding a New Navigation Pattern

### 1. Design and verify rotation math
```
Per-corner angle = 360° / N
Per-corner duration = (angle / 90) × 1.5 s
Total turn time = N × per-corner duration
Total degrees = total_turn_time × (90 / 1.5)
Must equal 360° for closed loops
```

### 2. Add to PLANNER_PROMPT in agent.py
```
── NEW PATTERN ───────────────────────────────────────────────
N × angle° = 360°. duration = (angle/90)×1.5 = X s.
total_turn_time = N × X = 6.0 s → 360°. ✓

  N× [forward(S) + direction(X)]  + stop
```

### 3. Add to _CLOSED_LOOP_PATTERNS (if closed loop)
```python
_CLOSED_LOOP_PATTERNS = frozenset({
    "circle", "square", "triangle", "pentagon",
    "hexagon", "oval", "spiral-out", "figure-forward",
    "your-new-pattern",   # ← add here
})
```

### 4. Add to print_patterns() in main.py
```python
("your-new-pattern", "Description of what it does"),
```

### 5. Add to patterns list in app_ui.py index()
```python
("your-new-pattern", "Description of what it does"),
```

---

## Adding a New Policy Provider

### 1. Subclass NavigationPolicy
```python
class MyPolicy(NavigationPolicy):
    def plan(self, user_request: str) -> Dict[str, Any]:
        # Return a validated plan dict
        plan = {...}
        validate_plan(plan)
        return plan

    @property
    def provider_name(self) -> str:
        return "my-provider"
```

### 2. Register in create_policy()
```python
def create_policy(provider: str = "nova", **kwargs) -> NavigationPolicy:
    table = {
        "nova": NovaPolicy,
        "mock": MockPolicy,
        "replay": ReplayPolicy,
        "my-provider": MyPolicy,   # ← add here
    }
```

---

## Adding a New @tool Function

### Template
```python
@tool
def deepracer_my_action(seconds: float = 2.0) -> str:
    """Docstring describing what this does and its physics constraints."""
    return _move_for_duration(
        steering=<value>,
        throttle=<value>,
        seconds=seconds,
    )
```

### Rules
- Must return a string (never raise to callers)
- Error strings must start with `"Error"` so `is_error()` detects them
- Add the action name to `VALID_ACTIONS` in agent.py
- Add to the dispatch dict in `execute_step()`
- Add to the PLANNER_PROMPT action list

---

## Adding a New DeepRacerTool Action

### 1. Add to tool_spec enum
```python
"enum": ["execute", "start", "status", "stop", "my-action"],
```

### 2. Add action method
```python
def _action_my_action(self, ...) -> Dict[str, Any]:
    ...
    return {"status": "success", "content": [{"text": "..."}]}
```

### 3. Add to dispatch in stream()
```python
dispatch = {
    "execute": lambda: self._action_execute(instruction),
    "start":   lambda: self._action_start(instruction),
    "status":  self._action_status,
    "stop":    self._action_stop,
    "my-action": lambda: self._action_my_action(...),
}
```

---

## Extending the Web UI

### Adding a new SSE event type
1. Define the event name and payload shape
2. Call `_push("my-event", {"field": value})` in the execution thread
3. Handle in the browser EventSource listener:
   ```javascript
   source.addEventListener("my-event", (e) => {
       const data = JSON.parse(e.data);
       // update UI
   });
   ```

### Adding a new route
```python
@app.route("/my-route", methods=["POST"])
def my_route():
    body = request.get_json(force=True)
    # ...
    return jsonify({"ok": True, "result": ...})
```

---

## Upgrading to Phase 3

Phase 3 adds visual navigation via camera feed. Key extension points:
- `NavigationPolicy` can be subclassed with a `VisionPolicy` that reads camera frames
- `DeepRacerTool` can be extended with `action=camera` to capture frames
- `deepracer_tools.py` can add `deepracer_get_frame()` as a new @tool
- The SSE stream can carry `frame` events with base64-encoded images
- `validate_plan()` remains unchanged — visual policies still produce the same plan schema
