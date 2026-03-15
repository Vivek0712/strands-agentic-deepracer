# Phase 2 StepResult and PlanResult — Requirements

## Overview
`StepResult` and `PlanResult` are dataclasses that provide structured, rich execution
feedback. They replace the bare `(step_dict, message_str)` tuples from Phase 1 and
enable the `DeepRacerTool` to produce detailed step logs.

## Functional Requirements

### FR-1: StepResult Dataclass
```python
@dataclass
class StepResult:
    step:    Dict[str, Any]   # the original step dict
    ok:      bool             # True if step succeeded
    message: str              # tool return message or exception text
```
- `ok` is set by `is_error(str(msg))` in `execute_step()`
- `message` is the raw tool return string or `f"Exception in '{action}': {exc}"`

### FR-2: StepResult.display()
- Returns a single formatted line: `"  {icon} {action}{dur}  →  {message}"`
- `icon` = `"✓"` when `ok=True`, `"✗"` when `ok=False`
- `dur` = `f" {seconds}s"` when seconds is not None, else `""`
- Used by `_build_payload()` in `DeepRacerTool` for the step log

### FR-3: PlanResult Dataclass
```python
@dataclass
class PlanResult:
    results:      List[StepResult] = field(default_factory=list)
    aborted:      bool             = False
    abort_reason: str              = ""
    pattern:      str              = "unknown"
    reasoning:    str              = ""
```
- `pattern` and `reasoning` populated from plan dict at construction
- `results` appended as steps execute
- `aborted` set to True when execution stops early

### FR-4: PlanResult.all_ok Property
- Returns `True` only when `not self.aborted and all(r.ok for r in self.results)`
- Empty results with no abort → `True` (vacuously)
- Any failed step OR aborted → `False`

### FR-5: PlanResult.completed_steps Property
- Returns `len(self.results)`
- Includes the failed step (the step that caused abort is appended before breaking)
- Does NOT include the emergency stop step (that's called directly, not via results)

### FR-6: execute_plan() Compatibility
- `execute_plan()` returns `List[Tuple[Dict, str]]` — compatible with Phase 1 `main.py` unpacking
- Internally uses `execute_step()` which returns `StepResult`
- Converts: `output.append((sr.step, sr.message))`

### FR-7: execute_plan_full() Rich Return
- Returns `PlanResult` — used by `deepracer_agent_tool.py`
- Populates `pattern` and `reasoning` from plan dict
- Appends each `StepResult` to `result.results`
- Sets `aborted=True` and `abort_reason` on failure

## Non-Functional Requirements
- NFR-1: `StepResult` and `PlanResult` are imported by `deepracer_agent_tool.py`
- NFR-2: `PlanResult` is constructed at the start of `execute_plan_full()` — not after
- NFR-3: `display()` output is used verbatim in `_build_payload()` step log
