import { resolveStageUrl } from "../api";

interface SideBySideViewerProps {
  originalUrl: string;
  originalPreviewUrl: string;
  finalUrl?: string;
}

export function SideBySideViewer({
  originalUrl,
  originalPreviewUrl,
  finalUrl,
}: SideBySideViewerProps) {
  return (
    <div style={{ display: "flex", gap: "2rem" }}>
      <div>
        <h3>Original</h3>
        <img
          src={originalPreviewUrl || resolveStageUrl(originalUrl)}
          alt="Original card"
          style={{ maxWidth: 320, border: "1px solid #ccc" }}
        />
      </div>
      <div>
        <h3>Processed (with bleed)</h3>
        {finalUrl ? (
          <img
            src={resolveStageUrl(finalUrl)}
            alt="Processed card with bleed"
            style={{ maxWidth: 320, border: "1px solid #ccc" }}
          />
        ) : (
          <p>Waiting for processing to complete…</p>
        )}
      </div>
    </div>
  );
}
