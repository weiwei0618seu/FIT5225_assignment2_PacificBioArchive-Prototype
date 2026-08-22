import { ApiError, getMedia, initiateUpload, putPresignedFile } from "../api/client";
import type { MediaRecord } from "../api/types";

export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
export const MAX_VIDEO_BYTES = 50 * 1024 * 1024;
export const ACCEPTED_MEDIA_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "video/mp4",
  "video/quicktime",
  "video/x-msvideo",
] as const;

export type UploadProgress = {
  phase: "hashing" | "reserving" | "uploading" | "processing";
  percent?: number;
  fileId?: string;
};

export class FileValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FileValidationError";
  }
}

export function validateMediaFile(file: File): void {
  if (!ACCEPTED_MEDIA_TYPES.includes(file.type as (typeof ACCEPTED_MEDIA_TYPES)[number])) {
    throw new FileValidationError("Choose a JPG, PNG, WebP, MP4, MOV or AVI file.");
  }
  const maximum = file.type.startsWith("image/") ? MAX_IMAGE_BYTES : MAX_VIDEO_BYTES;
  if (file.size < 1) throw new FileValidationError("The selected file is empty.");
  if (file.size > maximum) {
    throw new FileValidationError(
      `${file.type.startsWith("image/") ? "Images" : "Videos"} must be no larger than ${maximum / 1024 / 1024} MiB.`,
    );
  }
}

export async function sha256File(file: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export async function uploadAndWait(
  file: File,
  onProgress: (progress: UploadProgress) => void,
): Promise<MediaRecord> {
  validateMediaFile(file);
  onProgress({ phase: "hashing" });
  const checksum = await sha256File(file);
  onProgress({ phase: "reserving" });
  const ticket = await initiateUpload(file, checksum);
  onProgress({ phase: "uploading", percent: 0, fileId: ticket.file_id });
  await putPresignedFile(ticket, file, (percent) => {
    onProgress({ phase: "uploading", percent, fileId: ticket.file_id });
  });
  onProgress({ phase: "processing", fileId: ticket.file_id });

  for (let attempt = 0; attempt < 150; attempt += 1) {
    const media = await getMedia(ticket.file_id);
    if (media.processing_status === "READY") return media;
    if (media.processing_status === "FAILED") {
      throw new ApiError(
        "The upload was stored, but wildlife processing failed. You can retry with another file.",
        media.error_code || "PROCESSING_FAILED",
        422,
      );
    }
    await wait(2000);
  }
  throw new ApiError(
    "Processing is taking longer than expected. Keep the file ID and check again later.",
    "PROCESSING_TIMEOUT",
    408,
  );
}
