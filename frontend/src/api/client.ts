import { idToken } from "../auth/authClient";
import type { ApiErrorBody, MediaRecord, UploadTicket } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function apiBaseUrl(): string {
  const value = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!value) throw new Error("The API URL is not configured.");
  return value.replace(/\/$/, "");
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = await idToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as T & ApiErrorBody;
  if (!response.ok) {
    const error = payload.error;
    throw new ApiError(
      error?.message || `The request failed with status ${response.status}.`,
      error?.code || "REQUEST_FAILED",
      response.status,
      error?.request_id,
    );
  }
  return payload;
}

export function initiateUpload(file: File, checksum: string): Promise<UploadTicket> {
  return apiRequest<UploadTicket>("/uploads/init", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
      size_bytes: file.size,
      checksum,
    }),
  });
}

export function getMedia(fileId: string): Promise<MediaRecord> {
  return apiRequest<MediaRecord>(`/media/${encodeURIComponent(fileId)}`);
}

export function putPresignedFile(
  ticket: UploadTicket,
  file: File,
  onProgress: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", ticket.upload_url);
    for (const [name, value] of Object.entries(ticket.required_headers)) {
      request.setRequestHeader(name, value);
    }
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
      }
    };
    request.onerror = () => reject(new Error("The direct upload could not reach storage."));
    request.onabort = () => reject(new Error("The upload was cancelled."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        resolve();
      } else {
        reject(new Error(`Storage rejected the upload (HTTP ${request.status}).`));
      }
    };
    request.send(file);
  });
}
