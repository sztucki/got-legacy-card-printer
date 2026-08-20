import { useEffect, useState } from "react";
import type { CreateJobOptions } from "../api";
import { BleedTuningFields } from "./BleedTuningFields";
import { DEFAULT_FOOTER_HEIGHT_PERCENT, DEFAULT_MASK_BLUR, DEFAULT_STRENGTH } from "../bleedDefaults";
import { useUpscaleModels } from "../useUpscaleModels";

interface UploadFormProps {
  onUpload: (file: File, options: CreateJobOptions) => void;
  disabled: boolean;
}

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [rotateOverride, setRotateOverride] = useState<string>("auto");
  const models = useUpscaleModels();
  const [upscaleModel, setUpscaleModel] = useState<string>("");
  const [removeFooterText, setRemoveFooterText] = useState(true);
  const [footerHeightPercent, setFooterHeightPercent] = useState(DEFAULT_FOOTER_HEIGHT_PERCENT);
  const [sdStrength, setSdStrength] = useState(DEFAULT_STRENGTH);
  const [sdMaskBlur, setSdMaskBlur] = useState(DEFAULT_MASK_BLUR);
  const [seedText, setSeedText] = useState("");

  // Unlike RegenerateOptions, default to the first available model rather
  // than an empty "use backend default" selection - there's no prior job to
  // show "(keep as-is)" against yet.
  useEffect(() => {
    setUpscaleModel((current) => current || models[0] || "");
  }, [models]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (file) {
      const override = rotateOverride === "auto" ? null : rotateOverride === "true";
      onUpload(file, {
        rotateOverride: override,
        upscaleModel: upscaleModel || null,
        footerText: { remove: removeFooterText, heightFraction: footerHeightPercent / 100 },
        sdStrength,
        sdMaskBlur,
        sdSeed: seedText.trim() === "" ? null : Number(seedText),
      });
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        accept="image/*"
        disabled={disabled}
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <label style={{ marginLeft: "1rem" }}>
        Orientation:{" "}
        <select
          value={rotateOverride}
          disabled={disabled}
          onChange={(event) => setRotateOverride(event.target.value)}
        >
          <option value="auto">Auto-detect</option>
          <option value="false">Keep as-is</option>
          <option value="true">Rotate 90°</option>
        </select>
      </label>
      <label style={{ marginLeft: "1rem" }}>
        Upscale model:{" "}
        <select
          value={upscaleModel}
          disabled={disabled || models.length === 0}
          onChange={(event) => setUpscaleModel(event.target.value)}
        >
          {models.length === 0 && <option value="">(default)</option>}
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
      <button type="submit" disabled={disabled || !file} style={{ marginLeft: "1rem" }}>
        {disabled ? "Processing…" : "Process card"}
      </button>
    </form>
  );
}
