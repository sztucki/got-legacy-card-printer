import { useEffect, useState } from "react";
import { getUpscaleModels } from "../api";
import type { FooterTextOptions } from "../api";

interface UploadFormProps {
  onUpload: (
    file: File,
    rotateOverride: boolean | null,
    upscaleModel: string | null,
    footerText: FooterTextOptions | null
  ) => void;
  disabled: boolean;
}

const DEFAULT_FOOTER_HEIGHT_PERCENT = 8;

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [rotateOverride, setRotateOverride] = useState<string>("auto");
  const [models, setModels] = useState<string[]>([]);
  const [upscaleModel, setUpscaleModel] = useState<string>("");
  const [removeFooterText, setRemoveFooterText] = useState(false);
  const [footerHeightPercent, setFooterHeightPercent] = useState(DEFAULT_FOOTER_HEIGHT_PERCENT);

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
      const footerText: FooterTextOptions | null = removeFooterText
        ? { remove: true, heightFraction: footerHeightPercent / 100 }
        : null;
      onUpload(file, override, upscaleModel || null, footerText);
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
      <label style={{ marginLeft: "1rem" }}>
        <input
          type="checkbox"
          checked={removeFooterText}
          disabled={disabled}
          onChange={(event) => setRemoveFooterText(event.target.checked)}
        />{" "}
        Remove blurry footer text
      </label>
      {removeFooterText && (
        <label style={{ marginLeft: "1rem" }}>
          Footer height:{" "}
          <input
            type="number"
            min={1}
            max={30}
            step={0.5}
            value={footerHeightPercent}
            disabled={disabled}
            onChange={(event) => setFooterHeightPercent(Number(event.target.value))}
            style={{ width: "4rem" }}
          />
          %
        </label>
      )}
      <button type="submit" disabled={disabled || !file} style={{ marginLeft: "1rem" }}>
        {disabled ? "Processing…" : "Process card"}
      </button>
    </form>
  );
}
