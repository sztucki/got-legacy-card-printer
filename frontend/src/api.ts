const API_BASE = "http://localhost:8000";

export interface JobState {
  job_id: string;
  status: "pending" | "processing" | "complete" | "failed";
  error: string | null;
  stages: Record<string, boolean>;
  stage_urls: Record<string, string>;
}

export async function createJob(
  file: File,
  rotateOverride: boolean | null
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (rotateOverride !== null) {
    formData.append("rotate_override", String(rotateOverride));
  }

  const response = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.statusText}`);
  }
  return response.json();
}

export async function getJob(jobId: string): Promise<JobState> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job: ${response.statusText}`);
  }
  return response.json();
}

export function resolveStageUrl(url: string): string {
  return `${API_BASE}${url}`;
}
