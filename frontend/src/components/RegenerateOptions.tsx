import { useEffect, useState } from "react";
import { getUpscaleModels } from "../api";
import type { RegenerateBleedOptions } from "../api";
import { BleedTuningFields } from "./BleedTuningFields";

interface RegenerateOptionsProps {
  onRegenerate: (options: RegenerateBleedOptions) => void;
  disabled: boolean;
}

const DEFAULT_STRENGTH = 0.85;
const DEFAULT_MASK_BLUR = 12;
const DEFAULT_FOOTER_HEIGHT_PERCENT = 8;

export function RegenerateOptions({ onRegenerate, disabled }: RegenerateOptionsProps) {
  const [expanded, setExpanded] = useState(false);
  const [sdStrength, setSdStrength] = useState(DEFAULT_STRENGTH);
  const [sdMaskBlur, setSdMaskBlur] = useState(DEFAULT_MASK_BLUR);
  const [seedText, setSeedText] = useState("");
  const [removeFooterText, setRemoveFooterText] = useState(true);
  const [footerHeightPercent, setFooterHeightPercent] = useState(DEFAULT_FOOTER_HEIGHT_PERCENT);
  const [models, setModels] = useState<string[]>([]);
  const [upscaleModel, setUpscaleModel] = useState<string>("");

  useEffect(() => {
    getUpscaleModels()
      .then(({ models }) => setModels(models))
      .catch(() => {
        // Model list is a nice-to-have - re-upscaling just isn't offered if
        // it can't be fetched (upscale_model stays unset, i.e. "keep as-is").
      });
  }, []);

  function handleRegenerateClick() {
    onRegenerate({
      sdStrength,
      sdMaskBlur,
      sdSeed: seedText.trim() === "" ? null : Number(seedText),
      removeFooterText,
      footerHeightFraction: footerHeightPercent / 100,
      upscaleModel: upscaleModel || null,
    });
  }

  return (
    <div style={{ marginTop: "1rem" }}>
      <button onClick={handleRegenerateClick} disabled={disabled}>
        {disabled ? "Regenerating…" : "Regenerate bleed"}
      </button>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        disabled={disabled}
        style={{ marginLeft: "0.5rem" }}
      >
        {expanded ? "Hide options" : "Options…"}
      </button>

      {expanded && (
        <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem 0" }}>
          <label>
            Upscale model (re-upscales if changed):{" "}
            <select
              value={upscaleModel}
              disabled={disabled || models.length === 0}
              onChange={(event) => setUpscaleModel(event.target.value)}
            >
              <option value="">(keep as-is)</option>
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <BleedTuningFields
            sdStrength={sdStrength}
            onSdStrengthChange={setSdStrength}
            sdMaskBlur={sdMaskBlur}
            onSdMaskBlurChange={setSdMaskBlur}
            seedText={seedText}
            onSeedTextChange={setSeedText}
            removeFooterText={removeFooterText}
            onRemoveFooterTextChange={setRemoveFooterText}
            footerHeightPercent={footerHeightPercent}
            onFooterHeightPercentChange={setFooterHeightPercent}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
}
