# Phase 1: Static Assets — Requirements

## Overview
The web UI depends on three image assets served from the shared `assets/` directory at the project root. This spec covers asset paths, serving configuration, and fallback behaviour.

## Requirements

### REQ-ASSETS-1: Required Files
The following files MUST exist at `assets/` (project root, one level above `phase-1-agentic-navigation-planner/`):
| File | Purpose |
|---|---|
| `assets/strands-logo.png` | Strands brand logo in header |
| `assets/deepracer-logo.png` | DeepRacer brand logo in header |
| `assets/deepracer_bg.png` | Background texture image |

### REQ-ASSETS-2: Flask Static Serving
- `app_ui.py` MUST set `static_folder = BASE_DIR.parent / "assets"`
- `app_ui.py` MUST set `static_url_path = "/assets"`
- Assets MUST be accessible at `/assets/<filename>` URLs from the browser

### REQ-ASSETS-3: HTML References
- Strands logo: `<img src="/assets/strands-logo.png" alt="Strands logo">`
- DeepRacer logo: `<img src="/assets/deepracer-logo.png" alt="DeepRacer logo">`
- Background: referenced in CSS as `url("/assets/deepracer_bg.png")`
- All three references MUST use the `/assets/` prefix (not relative paths)

### REQ-ASSETS-4: Missing Asset Graceful Degradation
- Missing logo images MUST NOT break the UI layout — use `object-fit: contain` and fixed height
- Missing background image MUST NOT cause a JS error — CSS `background-image` fails silently
- The UI MUST remain fully functional even if all three assets are missing

### REQ-ASSETS-5: Asset Dimensions
- Logo images are displayed at `height: 32px` with `object-fit: contain`
- Background image uses `background-size: cover` and `background-position: center`
- No width constraints on logos — they scale proportionally
