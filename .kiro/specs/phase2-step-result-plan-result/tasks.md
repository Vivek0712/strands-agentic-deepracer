# Phase 2 StepResult and PlanResult — Tasks

## Task 1: Verify StepResult fields
- [ ] `step: Dict[str, Any]` — original step dict
- [ ] `ok: bool` — set by `not is_error(str(msg))`
- [ ] `message: str` — raw tool return or exception text

## Task 2: Verify StepResult.display() format
- [ ] `✓` icon when ok=True
- [ ] `✗` icon when ok=False
- [ ] Duration shown as `" {seconds}s"` when present
- [ ] Duration omitted for connect/stop steps
- [ ] Format: `"  {icon} {action}{dur}  →  {message}"`

## Task 3: Verify PlanResult fields and defaults
- [ ] `results` defaults to empty list via `field(default_factory=list)`
- [ ] `aborted` defaults to False
- [ ] `abort_reason` defaults to empty string
- [ ] `pattern` defaults to "unknown"
- [ ] `reasoning` defaults to empty string

## Task 4: Verify PlanResult.all_ok property
- [ ] Returns False when `aborted=True`
- [ ] Returns False when any `r.ok == False`
- [ ] Returns True when not aborted and all steps ok
- [ ] Returns True for empty results with no abort (vacuous truth)

## Task 5: Verify PlanResult.completed_steps property
- [ ] Returns `len(self.results)`
- [ ] Includes the failed step (appended before break)
- [ ] Does not include emergency stop (called directly)

## Task 6: Verify execute_plan() returns compatible tuples
- [ ] Returns `List[Tuple[Dict[str, Any], str]]`
- [ ] Each tuple is `(sr.step, sr.message)`
- [ ] `main.py` can unpack as `for step, message in results:`
- [ ] Emergency stop appended as `(emergency.step, f"[emergency] {emergency.message}")`

## Task 7: Verify execute_plan_full() populates PlanResult correctly
- [ ] `PlanResult(pattern=..., reasoning=...)` constructed at start
- [ ] Each `StepResult` appended to `result.results`
- [ ] On failure: `result.aborted = True`, `result.abort_reason = sr.message`
- [ ] `deepracer_agent_tool.py` uses `PlanResult` from `execute_plan_full()`

## Task 8: Verify _build_payload() uses display()
- [ ] `DeepRacerTool._build_payload()` iterates `s.result.results`
- [ ] Calls `sr.display()` for each step
- [ ] Appends to lines list for the content text
