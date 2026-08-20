import { useEffect, useRef, useState } from "react";
import { createJob, getJob, regenerateBleed } from "./api";
import type { CreateJobOptions, JobState, RegenerateBleedOptions } from "./api";
import { UploadForm } from "./components/UploadForm";
import { SideBySideViewer } from "./components/SideBySideViewer";
import { RegenerateOptions } from "./components/RegenerateOptions";
import "./App.css";

const POLL_INTERVAL_MS = 2000;

function App() {
  const [job, setJob] = useState<JobState | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string>("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [regenerateError, setRegenerateError] = useState<string | null>(null);
  const [bleedVersion, setBleedVersion] = useState(0);
  const pollRef = useRef<number | null>(null);
  const previewUrlRef = useRef<string>("");

  useEffect(() => {
    if (job?.status === "complete") {
      setBleedVersion((v) => v + 1);
    }
  }, [job?.status, job?.job_id]);

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  async function handleUpload(file: File, options: CreateJobOptions) {
    if (isUploading || isProcessing) return;

    setIsUploading(true);
    setUploadError(null);
    setJob(null);
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = URL.createObjectURL(file);
    setOriginalPreviewUrl(previewUrlRef.current);

    try {
      const { job_id } = await createJob(file, options);
      pollJob(job_id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
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

  async function handleRegenerate(options: RegenerateBleedOptions) {
    if (!job || isProcessing) return;
    setRegenerateError(null);
    try {
      await regenerateBleed(job.job_id, options);
      pollJob(job.job_id);
    } catch (err) {
      setRegenerateError(err instanceof Error ? err.message : "Regenerate failed");
    }
  }

  const isProcessing = job !== null && job.status !== "complete" && job.status !== "failed";

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Legacy Card Bleed Printer</h1>
      <UploadForm onUpload={handleUpload} disabled={isUploading || isProcessing} />

      {uploadError && <p style={{ color: "red" }}>{uploadError}</p>}
      {job && (
        <div style={{ marginTop: "2rem" }}>
          <p>Status: {job.status}</p>
          {job.status === "failed" && (
            <p style={{ color: "red" }}>Processing failed: {job.error}</p>
          )}
          <SideBySideViewer
            originalUrl={job.stage_urls.original}
            originalPreviewUrl={originalPreviewUrl}
            finalUrl={
              job.stage_urls.bleed
                ? `${job.stage_urls.bleed}?v=${bleedVersion}`
                : undefined
            }
          />
          {job.stage_urls.upscaled && (
            <div>
              <RegenerateOptions
                key={job.job_id}
                onRegenerate={handleRegenerate}
                disabled={isProcessing}
                jobParams={job.params}
              />
              {regenerateError && (
                <p style={{ color: "red" }}>{regenerateError}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
