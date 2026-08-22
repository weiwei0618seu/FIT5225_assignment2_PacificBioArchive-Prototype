import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { MediaRecord } from "../api/types";
import * as workflow from "../upload/uploadWorkflow";
import { UploadPage } from "./UploadPage";

vi.mock("../upload/uploadWorkflow", async () => {
  const actual = await vi.importActual<typeof import("../upload/uploadWorkflow")>("../upload/uploadWorkflow");
  return { ...actual, uploadAndWait: vi.fn() };
});

const readyMedia: MediaRecord = {
  file_id: "file-1",
  filename: "dingo.jpg",
  file_type: "image",
  species_counts: { dingo: 2 },
  auto_tags: ["dingo"],
  manual_tags: [],
  all_tags: ["dingo"],
  processing_status: "READY",
  error_code: null,
  detections: [],
  model_version: "supplied-v1",
  video_samples: null,
  original_url: "https://example.test/original",
  thumbnail_url: "https://example.test/thumb",
  created_at: "2026-08-23T00:00:00Z",
  updated_at: "2026-08-23T00:00:01Z",
  version: 3,
};

describe("upload workflow UI", () => {
  beforeEach(() => {
    vi.mocked(workflow.uploadAndWait).mockResolvedValue(readyMedia);
  });

  it("uploads a supported file and renders analysis", async () => {
    const user = userEvent.setup();
    render(<UploadPage />);
    const file = new File(["image bytes"], "dingo.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/choose an image or video/i), file);
    await user.click(screen.getByRole("button", { name: /upload and analyse/i }));
    expect(workflow.uploadAndWait).toHaveBeenCalledWith(file, expect.any(Function));
    expect(await screen.findByRole("heading", { name: /your media is ready/i })).toBeInTheDocument();
    expect(screen.getByText("dingo", { selector: "dt" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open original/i })).toHaveAttribute("href", readyMedia.original_url);
  });

  it("rejects an unsupported file before calling the API", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<UploadPage />);
    await user.upload(
      screen.getByLabelText(/choose an image or video/i),
      new File(["text"], "notes.txt", { type: "text/plain" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/choose a jpg/i);
    expect(workflow.uploadAndWait).not.toHaveBeenCalled();
  });

  it("explains checksum duplicates", async () => {
    const user = userEvent.setup();
    vi.mocked(workflow.uploadAndWait).mockRejectedValue(
      new ApiError("duplicate", "DUPLICATE_FILE", 409),
    );
    render(<UploadPage />);
    await user.upload(
      screen.getByLabelText(/choose an image or video/i),
      new File(["same bytes"], "same.jpg", { type: "image/jpeg" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and analyse/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already exist/i);
  });
});
