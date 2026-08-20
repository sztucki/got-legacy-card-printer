import { useEffect, useState } from "react";
import { getUpscaleModels } from "./api";

// Shared by UploadForm and RegenerateOptions - both offer an upscale-model
// picker backed by the same /api/upscale-models list.
export function useUpscaleModels(): string[] {
  const [models, setModels] = useState<string[]>([]);

  useEffect(() => {
    getUpscaleModels()
      .then(({ models }) => setModels(models))
      .catch(() => {
        // Model list is a nice-to-have - callers fall back to the backend's
        // own default (upscale_model omitted/unset) if it can't be fetched.
      });
  }, []);

  return models;
}
