import { useState } from "react";
import type { JobParams } from "./api";
import { DEFAULT_FOOTER_HEIGHT_PERCENT, DEFAULT_MASK_BLUR, DEFAULT_STRENGTH } from "./bleedDefaults";

export interface BleedTuningValues {
  sdStrength: number;
  sdMaskBlur: number;
  seedText: string;
  removeFooterText: boolean;
  footerHeightPercent: number;
}

export interface BleedTuningOptions {
  sdStrength: number;
  sdMaskBlur: number;
  sdSeed: number | null;
  removeFooterText: boolean;
  footerHeightFraction: number;
}

// Shared by UploadForm (seeded from the DEFAULT_* constants) and
// RegenerateOptions (seeded from the job's own last-used params) - both offer
// the same set of bleed-tuning fields via BleedTuningFields and need to turn
// them into the same options shape on submit.
export function useBleedTuningState(initial: Partial<JobParams> = {}) {
  const [sdStrength, setSdStrength] = useState(initial.sd_strength ?? DEFAULT_STRENGTH);
  const [sdMaskBlur, setSdMaskBlur] = useState(initial.sd_mask_blur ?? DEFAULT_MASK_BLUR);
  const [seedText, setSeedText] = useState("");
  const [removeFooterText, setRemoveFooterText] = useState(initial.remove_footer_text ?? true);
  const [footerHeightPercent, setFooterHeightPercent] = useState(
    (initial.footer_height_fraction ?? DEFAULT_FOOTER_HEIGHT_PERCENT / 100) * 100
  );

  function toOptions(): BleedTuningOptions {
    return {
      sdStrength,
      sdMaskBlur,
      sdSeed: seedText.trim() === "" ? null : Number(seedText),
      removeFooterText,
      footerHeightFraction: footerHeightPercent / 100,
    };
  }

  return {
    values: { sdStrength, sdMaskBlur, seedText, removeFooterText, footerHeightPercent },
    handlers: {
      onSdStrengthChange: setSdStrength,
      onSdMaskBlurChange: setSdMaskBlur,
      onSeedTextChange: setSeedText,
      onRemoveFooterTextChange: setRemoveFooterText,
      onFooterHeightPercentChange: setFooterHeightPercent,
    },
    toOptions,
  };
}
