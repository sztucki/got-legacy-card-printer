import { useState } from "react";
import type { JobParams, RegenerateBleedOptions } from "../api";
import { BleedTuningFields } from "./BleedTuningFields";
import { useBleedTuningState } from "../useBleedTuningState";
import { useUpscaleModels } from "../useUpscaleModels";

interface RegenerateOptionsProps {
  onRegenerate: (options: RegenerateBleedOptions) => Promise<void>;
  disabled: boolean;
  // The job's own last-used settings, so a bare "Regenerate bleed" click
  // (without opening "Options…") reuses what this card actually ran with -
  // e.g. doesn't silently re-enable footer-text removal if the user
  // explicitly turned it off at upload time. Render this component with
  // `key={job.job_id}` so it re-seeds fresh per job rather than carrying
  // stale state across uploads.
  jobParams: Partial<JobParams>;
}

export function RegenerateOptions({ onRegenerate, disabled, jobParams }: RegenerateOptionsProps) {
  const [expanded, setExpanded] = useState(false);
  const { values, handlers, toOptions } = useBleedTuningState(jobParams);
  const models = useUpscaleModels();
  // Deliberately not seeded from jobParams.upscale_model - re-upscaling is an
  // explicit, opt-in action (it's slower than a bleed-only re-roll), so this
  // stays "" ("keep as-is") until the user actually picks a model.
  const [upscaleModel, setUpscaleModel] = useState<string>("");
  // Disables the button the instant it's clicked, ahead of the parent's
  // `disabled` prop flipping (which only happens once the next poll response
  // comes back) - closes the window for a fast double-click to fire a second
  // request. The backend also guards against this server-side (409 on an
  // already-processing job), so this is purely to avoid a spurious error
  // message, not a correctness fix.
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isDisabled = disabled || isSubmitting;

  async function handleRegenerateClick() {
    const tuning = toOptions();
    setIsSubmitting(true);
    try {
      await onRegenerate({
        sdStrength: tuning.sdStrength,
        sdMaskBlur: tuning.sdMaskBlur,
        sdSeed: tuning.sdSeed,
        removeFooterText: tuning.removeFooterText,
        footerHeightFraction: tuning.footerHeightFraction,
        upscaleModel: upscaleModel || null,
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{ marginTop: "1rem" }}>
      <button onClick={handleRegenerateClick} disabled={isDisabled}>
        {isDisabled ? "Regenerating…" : "Regenerate bleed"}
      </button>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        disabled={isDisabled}
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
              disabled={isDisabled || models.length === 0}
              onChange={(event) => setUpscaleModel(event.target.value)}
            >
              <option value="">
                (keep as-is{jobParams.upscale_model ? ` - ${jobParams.upscale_model}` : ""})
              </option>
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <BleedTuningFields {...values} {...handlers} disabled={isDisabled} />
        </div>
      )}
    </div>
  );
}
