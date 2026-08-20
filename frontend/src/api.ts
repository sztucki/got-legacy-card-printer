const API_BASE = "http://localhost:8000";

export interface JobParams {
  upscale_model: string | null;
  remove_footer_text: boolean;
  footer_height_fraction: number;
  sd_strength: number | null;
  sd_mask_blur: number | null;
}

export interface JobState {
  job_id: string;
  status: "pending" | "processing" | "complete" | "failed";
  error: string | null;
  stages: Record<string, boolean>;
  stage_urls: Record<string, string>;
  params: Partial<JobParams>;
}

export interface FooterTextOptions {
  remove: boolean;
  heightFraction: number;
}

export interface CreateJobOptions {
  rotateOverride: boolean | null;
  upscaleModel: string | null;
  footerText: FooterTextOptions | null;
  sdStrength: number | null;
  sdMaskBlur: number | null;
  sdSeed: number | null;
}

export async function createJob(
  file: File,
  options: CreateJobOptions
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (options.rotateOverride !== null) {
    formData.append("rotate_override", String(options.rotateOverride));
  }
  if (options.upscaleModel !== null) {
    formData.append("upscale_model", options.upscaleModel);
  }
  if (options.footerText !== null) {
    formData.append("remove_footer_text", String(options.footerText.remove));
    formData.append("footer_height_fraction", String(options.footerText.heightFraction));
  }
  if (options.sdStrength !== null) {
    formData.append("sd_strength", String(options.sdStrength));
  }
  if (options.sdMaskBlur !== null) {
    formData.append("sd_mask_blur", String(options.sdMaskBlur));
  }
  if (options.sdSeed !== null) {
    formData.append("sd_seed", String(options.sdSeed));
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

export interface RegenerateBleedOptions {
  sdStrength: number | null;
  sdMaskBlur: number | null;
  sdSeed: number | null;
  removeFooterText: boolean;
  footerHeightFraction: number;
  upscaleModel: string | null;
}

export async function regenerateBleed(
  jobId: string,
  options: RegenerateBleedOptions
): Promise<{ job_id: string }> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/regenerate-bleed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sd_strength: options.sdStrength,
      sd_mask_blur: options.sdMaskBlur,
      sd_seed: options.sdSeed,
      remove_footer_text: options.removeFooterText,
      footer_height_fraction: options.footerHeightFraction,
      upscale_model: options.upscaleModel,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to regenerate bleed: ${response.statusText}`);
  }
  return response.json();
}

export function resolveStageUrl(url: string): string {
  return `${API_BASE}${url}`;
}
