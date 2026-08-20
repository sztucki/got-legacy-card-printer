# got-legacy-card-printer

A local POC web app that takes a legacy game card image and produces a print-ready
version: orients it to the correct side, upscales it, and generates an AI outpainted
bleed edge. Upload a card, watch it get processed, and compare the original and
processed versions side by side. See [PLAN.md](./PLAN.md) for the full design.

## Prerequisites

- Python 3.10+
- Node.js 18+
- [Upscayl](https://github.com/upscayl/upscayl) installed locally (desktop app or the
  bundled CLI). The desktop app's CLI binary is typically at:
  `/Applications/Upscayl.app/Contents/Resources/bin/upscayl-bin` on macOS.
- [IOPaint](https://github.com/Sanster/IOPaint) installed locally (`pip install iopaint`)
  for AI bleed outpainting - fully local/open-source, no API key or per-call cost.

## Setup

### IOPaint (bleed outpainting)

Runs as its own local server, separate from this app's backend - start it once and
leave it running (it keeps the model loaded in memory). Install it into its own venv
(not `backend/venv`) - IOPaint pins older versions of FastAPI/Pillow/etc. that conflict
with the backend's own requirements:

```sh
python3 -m venv iopaint-venv
iopaint-venv/bin/pip install iopaint
iopaint-venv/bin/iopaint start --model=runwayml/stable-diffusion-inpainting --device=mps
```

Use `--device=cuda` on an NVIDIA machine, or omit `--device` for CPU-only (much
slower). The model (~4GB) downloads on first run. Server listens on
`http://127.0.0.1:8080` by default, matching `IOPAINT_API_URL` in `.env.example`.

### Backend

```sh
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in UPSCAYL_BIN_PATH, UPSCAYL_MODELS_DIR
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### Frontend

```sh
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Reference cards

Drop sample cards that already have the correct bleed into `reference-cards/`
(gitignored) to compare pipeline output against and tune sizing/quality.

## Known issues (in progress)

- **IOPaint gets slower with each back-to-back generation, and can eventually time
  out**: observed on Apple Silicon (`--device=mps`) - successive outpainting calls
  within the same long-running `iopaint start` process take progressively longer
  (seen going from ~130s to ~200s+ over a handful of calls), consistent with MPS
  memory not being fully released between generations. If a job fails with
  `IOPaint server ... didn't respond within 300s`, restart the IOPaint server
  (`iopaint-venv/bin/iopaint start --model=... --device=mps`) to reset it. Not
  root-caused further - a fix would likely live upstream in IOPaint/diffusers, not
  in this app.
- Previously-reported "Failed to fetch" on upload did not reproduce in a clean run
  and is presumed fixed (see git history if it recurs).
- **Bleed generation still hallucinates/produces artifacts on some cards - pick this
  up next session**: `backend/app/pipeline/bleed.py`'s `SD_SEED` was changed from
  IOPaint's implicit default (42) to `123` after 42 produced a visible seam artifact
  in the leather-texture border on `reference-cards/card-to-enhance/The Roseroad.jpg`
  with the `high-fidelity-4x` upscale model - a seed-sensitivity issue confirmed by
  regenerating the exact same input with several seeds (42 bad, 7/123 clean, 9999 a
  different milder artifact - see chat history/session for the comparison images).
  123 fixed that *specific* case, verified via direct API call after restarting the
  backend. However, the user re-tested afterward through the frontend and is still
  seeing hallucinations - so a single fixed seed is not a real fix, just a
  better-odds gamble. Options not yet tried: randomize the seed per job (trades
  determinism for not getting permanently stuck on a bad roll - probably the more
  honest fix given this is fundamentally a per-generation stochastic quality
  problem, not a deterministic bug), add a "Regenerate bleed" endpoint/button so a
  bad result can be re-rolled without re-running the whole pipeline, or reduce
  `SD_STRENGTH`/tune the prompt further. Reproduce with
  `backend/scripts/tune_bleed.py` before making further changes - IOPaint must be
  freshly restarted first (see the slowdown issue above) so timing/behavior is
  representative.

## Assumptions to verify

- **Card dimensions**: `backend/app/config.py` is calibrated against
  `reference-cards/example-card/1_Bonifer_ENG.tif` (822x1122px @ 300 DPI = 69.6x95.0mm
  bleed-included), assuming a standard 3mm bleed margin per side. Update these
  constants if a different reference card suggests otherwise.
- **"Correct side"**: interpreted as orientation (rotation), not physical sizing. The
  app applies a best-guess rotation heuristic with a manual override.
- **IOPaint outpainting quality**: `runwayml/stable-diffusion-inpainting` is a
  reasonable general-purpose default. Bleed generation now runs *after* upscaling
  the trim to full print resolution (not before), giving IOPaint real pixel budget
  to work with instead of a handful of px that a later upscale would stretch into a
  flat/blurry band - this measurably improved border/texture continuation quality.
  Tunable parameters (prompt, negative prompt, mask blur, generation overshoot,
  steps, guidance scale) live as constants at the top of `backend/app/pipeline/bleed.py`;
  use `backend/scripts/tune_bleed.py` to compare variants quickly against images in
  `reference-cards/` without going through the full app. Still worth trying other
  IOPaint-supported inpainting models if quality is poor on other card styles.
