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

Three services run concurrently, each in its own terminal, in this order:

### 1. IOPaint (bleed outpainting)

Its own local server, separate from this app's backend - start it once and leave it
running (it keeps the model loaded in memory). Install it into its own venv (not
`backend/venv`) - IOPaint pins older versions of FastAPI/Pillow/etc. that conflict
with the backend's own requirements:

```sh
python3 -m venv iopaint-venv
iopaint-venv/bin/pip install iopaint
iopaint-venv/bin/iopaint start --model=runwayml/stable-diffusion-inpainting --device=mps
```

Use `--device=cuda` on an NVIDIA machine, or omit `--device` for CPU-only (much
slower). The model (~4GB) downloads on first run. Server listens on
`http://127.0.0.1:8080` by default, matching `IOPAINT_API_URL` in `.env.example`
(override in `backend/.env` if that port's taken).

### 2. Backend

```sh
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in UPSCAYL_BIN_PATH, UPSCAYL_MODELS_DIR
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. IOPaint must already be running (step 1) -
the backend calls out to it per job, it doesn't manage its lifecycle.

### 3. Frontend

```sh
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. Open that URL, upload a card, and watch it
process.

## Reference cards

Drop sample cards that already have the correct bleed into `reference-cards/`
(gitignored) to compare pipeline output against and tune sizing/quality.

## Regenerating / tuning bleed output

Bleed generation is a stochastic diffusion step, so results vary between
generations even with identical inputs. Rather than re-uploading to try a different
setting, the frontend's result view has a "Regenerate bleed" button with an
"Options…" panel that re-runs just the bleed step (and, if you change the upscale
model, that step too) against the already-uploaded card:

- **Strength** - how closely the generated margin sticks to the card's real edge
  pixels vs. inventing new content (`sd_strength`, default `0.85`).
- **Mask blur** - blend width at the seam between real and generated pixels
  (`sd_mask_blur`, default `12`).
- **Seed** - leave blank for a fresh random roll each time, or set a specific value
  to reproduce a result.
- **Upscale model** - pick a different Upscayl model; re-runs the upscale step too
  if changed.
- **Remove blurry footer text** - flat-fills the bottom band (illustrator credit /
  copyright / card number) before outpainting, at an adjustable height percentage
  (0.1% steps, so the cut line can be placed precisely per card). On by default -
  see "Known issues" below for why.

The same fields are available on the initial upload form too, so a card can be
generated with non-default settings from the start rather than only via regenerate.
`backend/scripts/tune_bleed.py` remains available as an offline/scripted equivalent
for batch comparisons across seeds and strengths without going through the browser.

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

### Resolved: bleed generation hallucinating text/artifacts

Bleed generation used to reliably hallucinate garbled pseudo-text in the bottom
margin, and this got worse (not better) the more the seed/strength/mask-blur knobs
were tuned in isolation - because the actual cause wasn't any of those knobs. Two
separate failure modes were in play:

1. **Garbled text**: `backend/app/pipeline/bleed.py`'s `_replicate_pad()` smears the
   trim's real edge pixels - including the real (if blurry) credit-line text right
   at the bottom edge - into the new margin before generation starts. The model then
   denoises from that smear at `sd_strength=0.85` and reconstructs it as garbled
   pseudo-text. A per-edge mask-blur "fix" was tried and found not to work: IOPaint
   thresholds any mask blur we send to hard binary before using it (see its own
   `iopaint/api.py`), so it only affects an internal blend step, never what the
   model actually generates. The real fix was removing the trigger: footer-text
   removal (`clean_text.py`'s `remove_footer_band()`) is now **default-on**, so
   there's no real text left for `_replicate_pad` to smear in the first place.
2. **Unrelated hallucinated imagery**: IOPaint's built-in `use_extender` outpainting
   mode was tried as an alternative generation path (it produced the best single
   result seen so far on one test card) but hard-codes `sd_strength=1.0` - full
   regeneration, ignoring source pixels entirely. Combined with default-on footer
   removal it did stop the text hallucination, but on closer inspection (zoomed in,
   not just at thumbnail scale) it hallucinated unrelated imagery - e.g. green
   landscape artwork bleeding into what should've been a flat footer bar - on 2/2
   tested seeds. This is the same "wild, unrelated content over plain regions"
   failure `use_extender` was avoided for originally, so it was reverted in favor of
   the manual `_replicate_pad`/`sd_strength=0.85` approach, which anchors to real
   source pixels and doesn't have this failure mode.

Confirmed fixed via both direct generation tests and the actual frontend. Some
residual seed-to-seed quality variance is expected (diffusion generation is
inherently stochastic) - use the regenerate/tuning feature above for a quick re-roll
if a specific result looks off, rather than treating any one bad roll as a
regression.

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
  Tunable parameters (prompt, negative prompt, strength, mask blur, seed,
  generation overshoot, steps, guidance scale) live as constants at the top of
  `backend/app/pipeline/bleed.py`, and strength/mask blur/seed are also adjustable
  per job from the frontend - see "Regenerating / tuning bleed output" above.
  `backend/scripts/tune_bleed.py` remains available to compare variants in bulk
  against images in `reference-cards/` without going through the full app. Still
  worth trying other IOPaint-supported inpainting models if quality is poor on
  other card styles.
