// Mirrors backend/app/pipeline/bleed.py's SD_STRENGTH/SD_MASK_BLUR and
// backend/app/pipeline/run.py's DEFAULT_FOOTER_HEIGHT_FRACTION - these are
// only used to pre-fill form fields (the backend applies its own defaults
// independently when a field is omitted), but keep them in sync if the
// backend defaults change, so the UI doesn't display a stale default.
export const DEFAULT_STRENGTH = 0.85;
export const DEFAULT_MASK_BLUR = 12;
export const DEFAULT_FOOTER_HEIGHT_PERCENT = 8;
