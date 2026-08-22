import {
  executeTemporaryQuery,
  initiateTemporaryQuery,
  putPresignedFile,
} from "../api/client";
import type { TemporaryQueryResponse } from "../api/types";
import {
  ACCEPTED_MEDIA_TYPES,
  FileValidationError,
  sha256File,
  validateMediaFile,
} from "../upload/uploadWorkflow";

export const ACCEPTED_QUERY_TYPES = ACCEPTED_MEDIA_TYPES.filter((type) => type.startsWith("image/"));

export type TemporaryQueryProgress = {
  phase: "hashing" | "uploading" | "analysing";
  percent?: number;
};

export function validateTemporaryQueryFile(file: File): void {
  validateMediaFile(file);
  if (!file.type.startsWith("image/")) {
    throw new FileValidationError("Similarity queries accept JPG, PNG or WebP images only.");
  }
}

export async function runTemporaryQuery(
  file: File,
  onProgress: (progress: TemporaryQueryProgress) => void,
): Promise<TemporaryQueryResponse> {
  validateTemporaryQueryFile(file);
  onProgress({ phase: "hashing" });
  const checksum = await sha256File(file);
  const ticket = await initiateTemporaryQuery(file, checksum);
  onProgress({ phase: "uploading", percent: 0 });
  await putPresignedFile(ticket, file, (percent) => onProgress({ phase: "uploading", percent }));
  onProgress({ phase: "analysing" });
  return executeTemporaryQuery(ticket);
}
