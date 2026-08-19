import { useEffect, useState } from "react";
import { getUpscaleModels } from "../api";

interface UploadFormProps {
  onUpload: (file: File, rotateOverride: boolean | null, upscaleModel: string | null) => void;
  disabled: boolean;
}

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [rotateOverride, setRotateOverride] = useState<string>("auto");
  const [models, setModels] = useState<string[]>([]);
  const [upscaleModel, setUpscaleModel] = useState<string>("");

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
      onUpload(file, override, upscaleModel || null);
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
      <button type="submit" disabled={disabled || !file} style={{ marginLeft: "1rem" }}>
        {disabled ? "Processing…" : "Process card"}
      </button>
    </form>
  );
}
