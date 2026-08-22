export type ProcessingStatus = "RESERVED" | "UPLOADED" | "PROCESSING" | "READY" | "FAILED";

export type Detection = {
  species?: string;
  combined_confidence?: number;
  detector_confidence?: number;
  classifier_confidence?: number;
  [key: string]: unknown;
};

export type MediaRecord = {
  file_id: string;
  filename: string;
  file_type: "image" | "video";
  species_counts: Record<string, number>;
  auto_tags: string[];
  manual_tags: string[];
  all_tags: string[];
  processing_status: ProcessingStatus;
  error_code: string | null;
  detections: Detection[];
  model_version: string | null;
  video_samples: number | null;
  original_url?: string;
  thumbnail_url?: string | null;
  created_at: string;
  updated_at: string;
  version: number;
};

export type UploadTicket = {
  file_id: string;
  object_key: string;
  upload_url: string;
  required_headers: Record<string, string>;
  expires_in: number;
  processing_status: ProcessingStatus;
};

export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    details?: Record<string, unknown>;
  };
};
