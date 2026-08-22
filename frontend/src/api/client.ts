import { idToken } from "../auth/authClient";
import type {
  ApiErrorBody,
  DeleteResponse,
  MediaRecord,
  QueryResponse,
  Subscription,
  SubscriptionLookup,
  TagEditResponse,
  TemporaryQueryResponse,
  TemporaryQueryTicket,
  ThumbnailLookup,
  UploadTicket,
} from "./types";

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

export function queryRequirements(requirements: Record<string, number>): Promise<QueryResponse> {
  return apiRequest<QueryResponse>("/queries/tags", {
    method: "POST",
    body: JSON.stringify({ requirements }),
  });
}

export function querySpecies(tag: string): Promise<QueryResponse> {
  return apiRequest<QueryResponse>(`/queries/species?tag=${encodeURIComponent(tag)}`);
}

export function lookupThumbnail(thumbnailUrl: string): Promise<ThumbnailLookup> {
  return apiRequest<ThumbnailLookup>("/queries/thumbnail", {
    method: "POST",
    body: JSON.stringify({ thumbnail_url: thumbnailUrl }),
  });
}

export function initiateTemporaryQuery(file: File, checksum: string): Promise<TemporaryQueryTicket> {
  return apiRequest<TemporaryQueryTicket>("/queries/file/init", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
      size_bytes: file.size,
      checksum,
    }),
  });
}

export function executeTemporaryQuery(ticket: TemporaryQueryTicket): Promise<TemporaryQueryResponse> {
  return apiRequest<TemporaryQueryResponse>(`/queries/file/${encodeURIComponent(ticket.query_id)}`, {
    method: "POST",
    body: JSON.stringify({ temp_key: ticket.temp_key }),
  });
}

type MediaIdentifiers = { fileIds?: string[]; urls?: string[] };

export function editMediaTags(
  identifiers: MediaIdentifiers,
  tags: string[],
  operation: 0 | 1,
): Promise<TagEditResponse> {
  return apiRequest<TagEditResponse>("/media/tags", {
    method: "POST",
    body: JSON.stringify({
      file_ids: identifiers.fileIds || [],
      urls: identifiers.urls || [],
      tags,
      operation,
    }),
  });
}

export function deleteMedia(identifiers: MediaIdentifiers): Promise<DeleteResponse> {
  return apiRequest<DeleteResponse>("/media/delete", {
    method: "POST",
    body: JSON.stringify({ file_ids: identifiers.fileIds || [], urls: identifiers.urls || [] }),
  });
}

export function getNotificationSubscription(): Promise<SubscriptionLookup> {
  return apiRequest<SubscriptionLookup>("/notifications/subscription");
}

export function setNotificationSubscription(tags: string[]): Promise<Subscription> {
  return apiRequest<Subscription>("/notifications/subscription", {
    method: "POST",
    body: JSON.stringify({ tags }),
  });
}

export async function deleteNotificationSubscription(): Promise<boolean> {
  const response = await apiRequest<{ deleted: boolean }>("/notifications/subscription", {
    method: "DELETE",
  });
  return response.deleted;
}

export function putPresignedFile(
  ticket: Pick<UploadTicket, "upload_url" | "required_headers">,
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
