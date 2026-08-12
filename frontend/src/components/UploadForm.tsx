import { useState } from "react";

interface UploadFormProps {
  onUpload: (file: File, rotateOverride: boolean | null) => void;
  disabled: boolean;
}

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [rotateOverride, setRotateOverride] = useState<string>("auto");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (file) {
      const override = rotateOverride === "auto" ? null : rotateOverride === "true";
      onUpload(file, override);
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
      <button type="submit" disabled={disabled || !file} style={{ marginLeft: "1rem" }}>
        {disabled ? "Processing…" : "Process card"}
      </button>
    </form>
  );
}
