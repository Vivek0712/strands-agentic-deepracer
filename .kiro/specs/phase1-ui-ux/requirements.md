# Phase 1: UI/UX — Requirements

## Overview
The web UI must be immediately usable without documentation. This spec covers the visual design, interaction patterns, accessibility basics, and responsive behaviour of `templates/index.html`.

## Requirements

### REQ-UX-1: Branding
- MUST display the Strands logo (`/assets/strands-logo.png`) and DeepRacer logo (`/assets/deepracer-logo.png`) side by side in the header
- MUST display a "Phase 1 · Planner" badge in the header
- MUST use the DeepRacer background image (`/assets/deepracer_bg.png`) at low opacity (≤ 20%) as a decorative overlay
- Logo images MUST have descriptive `alt` attributes

### REQ-UX-2: Input Experience
- The prompt input MUST have a descriptive placeholder (e.g. "Move forward 2 seconds, then turn left 1 second and stop")
- The input MUST have visible focus styling (border colour change + box shadow)
- The Plan button MUST be visually distinct (gradient, shadow)
- Pressing Enter in the input field SHOULD trigger the Plan button (keyboard shortcut)

### REQ-UX-3: Plan Display
- Steps MUST be displayed as a numbered ordered list
- Each step MUST show: action name + duration in seconds (if applicable)
- The plan panel MUST appear without a page reload (dynamic DOM update)
- The plan panel MUST be hidden until a plan is received

### REQ-UX-4: Button States
- Plan button: disabled + reduced opacity while planning
- Execute button: disabled + reduced opacity while executing
- All buttons MUST have `cursor: not-allowed` when disabled
- Hover states MUST include a subtle upward transform (`translateY(-1px)`) and shadow increase

### REQ-UX-5: Feedback States
- "Planning…" status text MUST appear immediately when Plan is clicked
- "Executing…" status text MUST appear immediately when Execute is clicked
- Result box MUST use distinct colours: blue (loading), green (success), red (error)
- Success message MUST include the step count: "Done. N step(s) executed."

### REQ-UX-6: Chat History
- User prompt MUST appear as a right-aligned bubble with a dark background
- Agent plan summary MUST appear as a left-aligned bubble with a teal-tinted background
- Chat history MUST be cleared on each new Plan request (one exchange at a time)
- Chat container MUST auto-scroll to the latest bubble

### REQ-UX-7: Responsive Layout
- Two-column layout (chat + plan) on screens wider than 768px
- Single-column stacked layout on screens 768px and narrower
- Card padding MUST reduce slightly on mobile
- All interactive elements MUST be touch-friendly (adequate tap target size)

### REQ-UX-8: Accessibility Basics
- `<html lang="en">` MUST be set
- All `<img>` elements MUST have `alt` attributes
- `<label>` MUST be associated with the prompt `<input>` via `for`/`id`
- Buttons MUST have descriptive text content (not just icons)
- Colour contrast MUST be sufficient for text on dark backgrounds
