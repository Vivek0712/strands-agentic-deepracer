# Phase 1: UI/UX — Implementation Tasks

## Task 1: Header & Branding
- [ ] Confirm `<img src="/assets/strands-logo.png" alt="Strands logo">` is present
- [ ] Confirm `<img src="/assets/deepracer-logo.png" alt="DeepRacer logo">` is present
- [ ] Confirm `.badge-phase` element contains "Phase 1 · Planner"
- [ ] Confirm `body::before` pseudo-element uses `deepracer_bg.png` at `opacity: 0.18`
- [ ] Confirm `<html lang="en">` is set

## Task 2: Input & Keyboard UX
- [ ] Confirm `<input id="prompt">` has a descriptive placeholder text
- [ ] Confirm `#prompt:focus` CSS rule changes border colour and adds box-shadow
- [ ] Add `keydown` event listener on `#prompt` — trigger `getPlanBtn.click()` on Enter key
- [ ] Confirm `<label for="prompt">` is associated with the input

## Task 3: Plan Panel
- [ ] Confirm `#planBox` has `style="display: none;"` initially
- [ ] Confirm `planSteps.innerHTML` is populated with `<li>` elements showing action + seconds
- [ ] Confirm `planBox.style.display = 'block'` is set after successful plan fetch
- [ ] Confirm step format: `"1. forward 2s"` or `"1. stop"` (no seconds for stop/connect)

## Task 4: Button States
- [ ] Confirm `getPlanBtn.disabled = true` during fetch, `= false` in finally
- [ ] Confirm `executeBtn.disabled = true` during execution, `= false` in finally
- [ ] Confirm CSS `button:disabled { opacity: 0.55; cursor: not-allowed; }`
- [ ] Confirm `.btn-primary:hover:not(:disabled)` has `transform: translateY(-1px)`
- [ ] Confirm `.btn-success:hover:not(:disabled)` has `transform: translateY(-1px)`

## Task 5: Feedback States
- [ ] Confirm `setStatus('Planning…')` is called before fetch in getPlanBtn handler
- [ ] Confirm `setStatus('Executing…')` is called before fetch in executeBtn handler
- [ ] Confirm `setStatus('')` is called after both fetches complete
- [ ] Confirm `showResult('Executing plan…', 'loading')` shows blue box during execution
- [ ] Confirm success shows `"Done. N step(s) executed."` with `'success'` class (green)
- [ ] Confirm errors show `data.error` with `'error'` class (red)

## Task 6: Chat Bubbles
- [ ] Confirm `chatHistory.innerHTML = ''` clears history before adding new bubbles
- [ ] Confirm user bubble uses class `chat-user` (right-aligned, dark background)
- [ ] Confirm agent bubble uses class `chat-agent` (left-aligned, teal-tinted background)
- [ ] Confirm `chatHistory.scrollTop = chatHistory.scrollHeight` after appending bubble
- [ ] Confirm `formatPlanSummary()` produces readable summary string

## Task 7: Responsive Layout
- [ ] Confirm `.chat-layout` uses `grid-template-columns: minmax(0, 3fr) minmax(0, 2.3fr)`
- [ ] Confirm `@media (max-width: 768px)` sets `grid-template-columns: minmax(0, 1fr)`
- [ ] Confirm card padding reduces on mobile
- [ ] Test layout at 375px width — confirm single column, no horizontal overflow

## Task 8: Cancel Flow
- [ ] Confirm `cancelBtn` sets `planBox.style.display = 'none'`
- [ ] Confirm `cancelBtn` sets `currentPlan = null`
- [ ] Confirm `cancelBtn` calls `hideResult()`
- [ ] Confirm `cancelBtn` calls `setStatus('')`
