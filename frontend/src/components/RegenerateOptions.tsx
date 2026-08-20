import { useEffect, useState } from "react";
import { getUpscaleModels } from "../api";
import type { JobParams, RegenerateBleedOptions } from "../api";
import { BleedTuningFields } from "./BleedTuningFields";

interface RegenerateOptionsProps {
  onRegenerate: (options: RegenerateBleedOptions) => void;
  disabled: boolean;
  // The job's own last-used settings, so a bare "Regenerate bleed" click
  // (without opening "Options…") reuses what this card actually ran with -
  // e.g. doesn't silently re-enable footer-text removal if the user
  // explicitly turned it off at upload time. Render this component with
  // `key={job.job_id}` so it re-seeds fresh per job rather than carrying
  // stale state across uploads.
  jobParams: Partial<JobParams>;
}

const DEFAULT_STRENGTH = 0.85;
const DEFAULT_MASK_BLUR = 12;
const DEFAULT_FOOTER_HEIGHT_PERCENT = 8;

export function RegenerateOptions({ onRegenerate, disabled, jobParams }: RegenerateOptionsProps) {
  const [expanded, setExpanded] = useState(false);
  const [sdStrength, setSdStrength] = useState(jobParams.sd_strength ?? DEFAULT_STRENGTH);
  const [sdMaskBlur, setSdMaskBlur] = useState(jobParams.sd_mask_blur ?? DEFAULT_MASK_BLUR);
  const [seedText, setSeedText] = useState("");
  const [removeFooterText, setRemoveFooterText] = useState(jobParams.remove_footer_text ?? true);
  const [footerHeightPercent, setFooterHeightPercent] = useState(
    (jobParams.footer_height_fraction ?? DEFAULT_FOOTER_HEIGHT_PERCENT / 100) * 100
  );
  const [models, setModels] = useState<string[]>([]);
  const [upscaleModel, setUpscaleModel] = useState<string>(jobParams.upscale_model ?? "");

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
