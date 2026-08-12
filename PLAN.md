# Legacy Card Bleed Printer — POC Web App

> **Update**: bleed generation was switched from the OpenAI images API to a
> locally-run [IOPaint](https://github.com/Sanster/IOPaint) server (open
> source, no per-call cost) - see README.md for current setup. The original
> decisions below are kept as a historical record of the initial design.

## Context

`got-legacy-card-printer` currently contains only a placeholder README — this is a greenfield build. The goal is a local-only POC web app that takes a legacy game card image (correct trim size, but no printer's bleed) and produces a print-ready version: reoriented if needed, upscaled via Upscayl, and extended with an AI-generated bleed edge that plausibly continues the card's artwork outward. The user will drop in reference cards (already at the correct bleed-included size) to compare against and tune the pipeline. The app should let you upload a card, watch it get processed, and view the original and processed card side by side.

Decisions already confirmed with the user:
- **Stack**: Python (FastAPI) backend + a simple React (Vite) frontend.
- **Upscaling**: shell out to the Upscayl CLI as a subprocess.
- **Bleed generation**: OpenAI images API (`gpt-image-1` edit/outpaint endpoint) using a mask that protects the existing card art and lets the model fill in the new border.
- **Card dimensions**: standard trading card size — 2.5"×3.5" (63×88mm) trim, 2.72"×3.72" (69×94.5mm) bleed-included (~0.125"/3mm bleed per side) — kept as config constants, not hardcoded inline, so they're easy to correct once real reference cards are in hand.
- Reference cards and the local Upscayl install are the user's responsibility to add; the plan accounts for both being absent right now.

## Implementation steps

0. Copy this plan into the repo as `got-legacy-card-printer/PLAN.md` (first step, before any code).
1. Scaffold the structure below and wire up the pipeline stages.

## Pipeline

Each upload becomes a job with a working folder (`jobs/{job_id}/`) holding the output of every stage, so the frontend can show progress and, later, a stage-by-stage view — not just start/end.

1. **Ingest** — save the uploaded file as `00-original.*`.
2. **Orient** — normalize to the "correct side." MVP heuristic: compare the upload's aspect ratio to the target trim aspect ratio both as-is and rotated 90°; rotate if that's the closer match. Expose a manual rotate override in the UI since the heuristic will be wrong sometimes. Output `01-oriented.png`.
3. **Normalize size** — crop/pad to the trim aspect ratio at a clean working resolution. Output `02-normalized.png`.
4. **Upscale** — call the Upscayl CLI as a subprocess to reach the pixel dimensions needed for the bleed size at the target DPI (default 600 DPI, configurable). Output `03-upscaled.png`.
5. **Generate bleed** — place the upscaled trim image centered on a canvas sized to the bleed dimensions, build a mask that protects the trim area and exposes only the new border ring, and call the OpenAI images edit endpoint to outpaint the border. Output `04-bleed.png` (final).
6. **Serve** — job status/results endpoint returns URLs for original and final (and intermediate stages) for the frontend to render side by side.

This is a synchronous-per-job POC (no queue needed) but the endpoint should still be poll-friendly (`GET /api/jobs/{id}`) since the outpainting call can take 10–30s.

## Structure

```
got-legacy-card-printer/
  backend/
    app/
      main.py              # FastAPI app, routes
      config.py             # trim/bleed sizes, DPI, mm<->px helpers
      pipeline/
        orient.py
        normalize.py
        upscale.py           # subprocess wrapper around Upscayl CLI
        bleed.py              # canvas compose + mask + OpenAI edit call
        run.py                 # orchestrates the stages, writes job files
      jobs.py                 # job folder/state management
    requirements.txt          # fastapi, uvicorn, pillow, openai, python-multipart
    .env.example               # OPENAI_API_KEY, UPSCAYL_BIN_PATH
  frontend/
    src/
      App.tsx
      components/UploadForm.tsx
      components/SideBySideViewer.tsx
      api.ts                    # fetch wrappers for /api/jobs
    (standard Vite + React + TS scaffold)
  reference-cards/            # user drops correct-bleed sample cards here (gitignored)
  README.md                   # updated: setup, Upscayl install note, env vars, run instructions
```

## Key implementation notes

- **Upscayl CLI location**: not installed on this machine yet. `UPSCAYL_BIN_PATH` is an env var the user sets after installing Upscayl (the desktop app bundles the CLI binary; the README will explain how to find it, or the user can install `realesrgan-ncnn-vulkan` directly). The subprocess wrapper should fail with a clear error if the binary isn't found/configured, rather than silently skipping upscaling.
- **OpenAI outpainting**: use `OPENAI_API_KEY` from env; call the images edit endpoint with the composed canvas + mask. Keep the prompt focused on "extend the existing card border/art outward, matching style, no new text or elements."
- **Config, not constants-in-code**: trim size, bleed size, and DPI live in `config.py` so they're a one-line change once real reference cards confirm the actual target dimensions (flagged to the user as an assumption to verify).
- **"Correct side" is an assumption**: interpreted as orientation (rotation), not sizing. Flagged in the README as something to confirm once real legacy cards are in hand — the manual override control covers us if the heuristic is wrong.

## Verification

- Run backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`) locally.
- Upload a sample legacy card (once the user provides one) through the UI, confirm each pipeline stage completes and the job endpoint returns all stage image URLs.
- Confirm the side-by-side view renders original vs. final correctly.
- Once reference cards are dropped into `reference-cards/`, visually compare final pipeline output against them for size, bleed style, and orientation correctness — this is the real acceptance check for the POC, more than any automated test.
