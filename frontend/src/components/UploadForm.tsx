import { useEffect, useState } from "react";
import { getUpscaleModels } from "../api";
import type { CreateJobOptions } from "../api";
import { BleedTuningFields } from "./BleedTuningFields";
import { DEFAULT_FOOTER_HEIGHT_PERCENT, DEFAULT_MASK_BLUR, DEFAULT_STRENGTH } from "../bleedDefaults";

interface UploadFormProps {
  onUpload: (file: File, options: CreateJobOptions) => void;
  disabled: boolean;
}

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [rotateOverride, setRotateOverride] = useState<string>("auto");
  const [models, setModels] = useState<string[]>([]);
  const [upscaleModel, setUpscaleModel] = useState<string>("");
  const [removeFooterText, setRemoveFooterText] = useState(true);
  const [footerHeightPercent, setFooterHeightPercent] = useState(DEFAULT_FOOTER_HEIGHT_PERCENT);
  const [sdStrength, setSdStrength] = useState(DEFAULT_STRENGTH);
  const [sdMaskBlur, setSdMaskBlur] = useState(DEFAULT_MASK_BLUR);
  const [seedText, setSeedText] = useState("");

  useEffect(() => {
    getUpscaleModels()
      .then(({ models }) => {
        setModels(models);
        setUpscaleModel((current) => current || models[0] || "");
      })
      .catch(() => {
        // Model list is a nice-to-have - fall back to the backend's own
        // default (upscale_model omitted) if it can't be fetched.
      });
  }, []);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (file) {
      const override = rotateOverride === "auto" ? null : rotateOverride === "true";
      onUpload(file, {
        rotateOverride: override,
        upscaleModel: upscaleModel || null,
        footerText: removeFooterText
          ? { remove: true, heightFraction: footerHeightPercent / 100 }
          : { remove: false, heightFraction: footerHeightPercent / 100 },
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
