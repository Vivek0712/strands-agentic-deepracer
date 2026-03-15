# Phase 1: Static Assets — Tasks

## Task 1: Verify Asset Files Exist
- [ ] Confirm `assets/strands-logo.png` exists at project root
- [ ] Confirm `assets/deepracer-logo.png` exists at project root
- [ ] Confirm `assets/deepracer_bg.png` exists at project root

## Task 2: Flask Static Config
- [ ] Confirm `BASE_DIR = Path(__file__).resolve().parent` in `app_ui.py`
- [ ] Confirm `ASSETS_DIR = BASE_DIR.parent / "assets"` in `app_ui.py`
- [ ] Confirm `Flask(__name__, ..., static_folder=ASSETS_DIR, static_url_path="/assets")`
- [ ] Start `app_ui.py` and confirm `GET /assets/strands-logo.png` returns 200

## Task 3: HTML Asset References
- [ ] Confirm `<img src="/assets/strands-logo.png" alt="Strands logo">` in `index.html`
- [ ] Confirm `<img src="/assets/deepracer-logo.png" alt="DeepRacer logo">` in `index.html`
- [ ] Confirm `background-image: url("/assets/deepracer_bg.png")` in CSS
- [ ] Confirm no relative paths like `../assets/` or `./assets/` are used

## Task 4: Graceful Degradation Test
- [ ] Temporarily rename `assets/strands-logo.png` — confirm UI layout is not broken
- [ ] Confirm broken image shows alt text "Strands logo" (not a broken icon that shifts layout)
- [ ] Confirm `height: 32px` on `.brand-logos img` keeps header height stable
- [ ] Restore the file after testing

## Task 5: CSS Background Config
- [ ] Confirm `body::before` pseudo-element has `background-image: url("/assets/deepracer_bg.png")`
- [ ] Confirm `background-size: cover` and `background-position: center`
- [ ] Confirm `opacity: 0.18` (≤ 20% as required)
- [ ] Confirm `pointer-events: none` so the overlay doesn't block clicks
- [ ] Confirm `z-index: -2` so it stays behind all content
