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
leave it running (it keeps the model loaded in memory):

```sh
pip install iopaint
iopaint start --model=runwayml/stable-diffusion-inpainting --device=mps
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

- **Frontend "Failed to fetch" on upload**: seen while testing locally with the backend
  (port 8000), IOPaint (port 8090), and frontend (port 5173) all running. Backend log
  showed three `POST /api/jobs` requests landing in quick succession right after
  several `uvicorn --reload` restarts (triggered by live edits to `bleed.py`) -
  possibly the reloads dropping an in-flight connection, or a leftover multi-submit
  from before the double-click fix in `App.tsx` took effect via HMR. Not yet
  root-caused - pick this up next session by reproducing without concurrent backend
  edits/reloads and checking the browser console for the actual failed request.

## Assumptions to verify

- **Card dimensions**: `backend/app/config.py` is calibrated against
  `reference-cards/example-card/1_Bonifer_ENG.tif` (822x1122px @ 300 DPI = 69.6x95.0mm
  bleed-included), assuming a standard 3mm bleed margin per side. Update these
  constants if a different reference card suggests otherwise.
- **"Correct side"**: interpreted as orientation (rotation), not physical sizing. The
  app applies a best-guess rotation heuristic with a manual override.
- **IOPaint outpainting quality**: `runwayml/stable-diffusion-inpainting` is a
  reasonable general-purpose default, but hasn't been tuned against real legacy card
  art - try other IOPaint-supported inpainting models if bleed quality is poor.
