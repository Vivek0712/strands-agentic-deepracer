# Phase 1: Planner Agent — Design

## Responsibilities
`agent.py` is the pure-logic layer. It has no I/O, no Flask, no terminal interaction. It is imported by both `main.py` and `app_ui.py`.

## create_planner()

```python
def create_planner(model: str | None = None) -> Agent:
    m = model or os.getenv("MODEL", DEFAULT_MODEL)
    return Agent(
        model=m,
        tools=[],
        system_prompt=PLANNER_PROMPT,
    )
```

- `tools=[]` is intentional — the planner only generates JSON, never executes
- The agent is cheap to create but should be cached by callers (main.py creates once; app_ui.py uses singleton)

## plan_navigation()

```
planner(user_request)
    │
    ▼
raw response (dict or str)
    │
    ├─ if dict → use directly
    └─ if str  → strip ``` fences → json.loads()
                      │
                      ▼
              validate "steps" is a list
                      │
                      ▼
              return plan dict
```

### Fence Stripping Logic
```python
if text.startswith("```"):
    text = text.strip("`")
    if "\n" in text:
        text = "\n".join(text.split("\n")[1:])  # drop language hint line
```

## execute_step() Dispatch Table

| action | tool called | seconds used |
|---|---|---|
| `connect` | `deepracer_connect()` | no |
| `forward` | `deepracer_move_forward(seconds)` | yes |
| `backward` | `deepracer_move_backward(seconds)` | yes |
| `left` | `deepracer_turn_left(seconds)` | yes |
| `right` | `deepracer_turn_right(seconds)` | yes |
| `stop` | `deepracer_stop()` | no |
| anything else | return skip string | — |

### seconds Resolution
```python
if action in {"forward", "backward", "left", "right"}:
    if seconds is None:
        seconds = 2.0
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        seconds = 2.0
```

## execute_plan() Contract

```python
def execute_plan(plan: Dict) -> List[Tuple[Dict, str]]:
    results = []
    for step in plan.get("steps", []):
        result = execute_step(step)   # never raises
        results.append((step, result))
    return results
```

No short-circuiting. No I/O. Pure data transformation.

## PLANNER_PROMPT Design

The prompt is structured in three sections:
1. Role declaration — "You are a navigation planner for an AWS DeepRacer car"
2. Output format — exact JSON schema with field descriptions
3. Rules — duration defaults, stop/connect field rules, circle/u-turn handling, safety fallback

The prompt deliberately does NOT include examples (few-shot) to keep token usage low with Nova Lite.
