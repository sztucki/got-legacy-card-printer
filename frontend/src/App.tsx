import { useEffect, useRef, useState } from "react";
import { createJob, getJob } from "./api";
import type { JobState } from "./api";
import { UploadForm } from "./components/UploadForm";
import { SideBySideViewer } from "./components/SideBySideViewer";
import "./App.css";

const POLL_INTERVAL_MS = 2000;

function App() {
  const [job, setJob] = useState<JobState | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string>("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const previewUrlRef = useRef<string>("");

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  async function handleUpload(file: File, rotateOverride: boolean | null) {
    setUploadError(null);
    setJob(null);
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = URL.createObjectURL(file);
    setOriginalPreviewUrl(previewUrlRef.current);

    try {
      const { job_id } = await createJob(file, rotateOverride);
      pollJob(job_id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  function pollJob(jobId: string) {
    if (pollRef.current) window.clearInterval(pollRef.current);

    const poll = async () => {
      const state = await getJob(jobId);
      setJob(state);
      if (state.status === "complete" || state.status === "failed") {
        if (pollRef.current) window.clearInterval(pollRef.current);
      }
    };

    poll();
    pollRef.current = window.setInterval(poll, POLL_INTERVAL_MS);
  }

  const isProcessing = job !== null && job.status !== "complete" && job.status !== "failed";

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Legacy Card Bleed Printer</h1>
      <UploadForm onUpload={handleUpload} disabled={isProcessing} />

      {uploadError && <p style={{ color: "red" }}>{uploadError}</p>}
      {job?.status === "failed" && (
        <p style={{ color: "red" }}>Processing failed: {job.error}</p>
      )}
      {job && job.status !== "failed" && (
        <div style={{ marginTop: "2rem" }}>
          <p>Status: {job.status}</p>
          <SideBySideViewer
            originalUrl={job.stage_urls.original}
            originalPreviewUrl={originalPreviewUrl}
            finalUrl={job.stage_urls.bleed}
          />
        </div>
      )}
    </div>
  );
}

export default App;
