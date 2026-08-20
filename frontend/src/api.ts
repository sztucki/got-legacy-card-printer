const API_BASE = "http://localhost:8000";

export interface JobState {
  job_id: string;
  status: "pending" | "processing" | "complete" | "failed";
  error: string | null;
  stages: Record<string, boolean>;
  stage_urls: Record<string, string>;
}

export interface FooterTextOptions {
  remove: boolean;
  heightFraction: number;
}

export async function createJob(
  file: File,
  rotateOverride: boolean | null,
  upscaleModel: string | null,
  footerText: FooterTextOptions | null
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (rotateOverride !== null) {
    formData.append("rotate_override", String(rotateOverride));
  }
  if (upscaleModel !== null) {
    formData.append("upscale_model", upscaleModel);
  }
  if (footerText !== null) {
    formData.append("remove_footer_text", String(footerText.remove));
    formData.append("footer_height_fraction", String(footerText.heightFraction));
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

export async function getUpscaleModels(): Promise<{ models: string[] }> {
  const response = await fetch(`${API_BASE}/api/upscale-models`);
  if (!response.ok) {
    throw new Error(`Failed to fetch upscale models: ${response.statusText}`);
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
