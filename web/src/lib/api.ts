import type { Engagement } from "./checklist";
import { cloneMockEngagement } from "./mock-data";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

const configuredMaxMb = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? "100");
export const MAX_UPLOAD_BYTES =
  (Number.isFinite(configuredMaxMb) && configuredMaxMb > 0 ? configuredMaxMb : 100) *
  1024 *
  1024;

async function responseError(response: Response): Promise<Error> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) detail = body.detail;
  } catch {
    // The status-only message is safe and useful when the response is not JSON.
  }
  return new Error(detail);
}

export async function getEngagement(): Promise<Engagement> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    return cloneMockEngagement();
  }
  const response = await fetch(`${API_URL}/engagements/current`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as Engagement;
}

export async function uploadDocument(
  engagementId: string,
  itemId: string,
  file: File,
  onProgress: (pct: number) => void,
): Promise<void> {
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error(`File is larger than ${Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)} MB.`);
  }
  if (USE_MOCKS) {
    for (const pct of [20, 45, 70, 100]) {
      await new Promise((resolve) => setTimeout(resolve, 120));
      onProgress(pct);
    }
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(
      "POST",
      `${API_URL}/engagements/${encodeURIComponent(engagementId)}/items/${encodeURIComponent(itemId)}/documents`,
    );
    request.withCredentials = true;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress((event.loaded / event.total) * 100);
    };
    request.onerror = () => reject(new Error("Upload failed because the API could not be reached."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        resolve();
        return;
      }
      let message = `Upload failed (${request.status}).`;
      try {
        const body = JSON.parse(request.responseText) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // Keep the status-only message for non-JSON responses.
      }
      reject(new Error(message));
    };
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}
