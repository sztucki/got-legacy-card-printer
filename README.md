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
  `/Applications/upscayl.app/Contents/Resources/bin/upscayl-bin` on macOS.
- An OpenAI API key with access to the images API (`gpt-image-1`).

## Setup

### Backend

```sh
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in OPENAI_API_KEY and UPSCAYL_BIN_PATH
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

## Assumptions to verify

- **Card dimensions**: `backend/app/config.py` assumes standard trading card size
  (2.5"x3.5" trim, 2.72"x3.72" bleed-included, ~0.125" bleed per side). Update these
  constants once real reference cards confirm the actual target dimensions.
- **"Correct side"**: interpreted as orientation (rotation), not physical sizing. The
  app applies a best-guess rotation heuristic with a manual override.
- **Upscayl CLI flags**: `backend/app/pipeline/upscale.py` assumes `-i`/`-o` flags
  matching the realesrgan-ncnn-vulkan CLI Upscayl bundles; adjust if your installed
  binary differs.
