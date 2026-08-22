import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MediaRecord } from "../api/types";
import * as api from "../api/client";
import { ManagePage } from "./ManagePage";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, deleteMedia: vi.fn(), deleteNotificationSubscription: vi.fn(), editMediaTags: vi.fn(), getNotificationSubscription: vi.fn(), querySpecies: vi.fn(), setNotificationSubscription: vi.fn() };
});

const media: MediaRecord = {
  file_id: "owned-1", filename: "dingo.jpg", file_type: "image", species_counts: { dingo: 1 }, auto_tags: ["dingo"], manual_tags: [], all_tags: ["dingo"], processing_status: "READY", error_code: null, detections: [], model_version: "supplied-v1", video_samples: null, thumbnail_url: "https://example.test/thumb", original_url: "https://example.test/full", created_at: "2026-08-23T00:00:00Z", updated_at: "2026-08-23T00:00:00Z", version: 2,
};

describe("management UI", () => {
  beforeEach(() => {
    vi.mocked(api.getNotificationSubscription).mockResolvedValue({ subscription: null });
    vi.mocked(api.querySpecies).mockResolvedValue({ media: [media], total: 1, truncated: false });
  });

  async function selectMedia(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText(/species or tag/i), "dingo");
    await user.click(screen.getByRole("button", { name: /find media/i }));
    await user.click(await screen.findByRole("checkbox", { name: /select/i }));
  }

  it("selects query results and adds normalized bulk tags", async () => {
    const user = userEvent.setup();
    vi.mocked(api.editMediaTags).mockResolvedValue({ operation: 1, changed_tags: { "owned-1": ["night", "reviewed"] }, media: [{ ...media, manual_tags: ["night", "reviewed"], all_tags: ["dingo", "night", "reviewed"] }] });
    render(<ManagePage />);
    await selectMedia(user);
    await user.type(screen.getByLabelText(/manual tags/i), "night, reviewed");
    await user.click(screen.getByRole("button", { name: /apply tags/i }));
    expect(api.editMediaTags).toHaveBeenCalledWith({ fileIds: ["owned-1"], urls: [] }, ["night", "reviewed"], 1);
    expect(await screen.findByRole("status")).toHaveTextContent(/added 2 tag changes/i);
  });

  it("requires explicit confirmation before complete deletion", async () => {
    const user = userEvent.setup();
    vi.mocked(api.deleteMedia).mockResolvedValue({ complete: true, outcomes: [{ identifier: "owned-1", file_id: "owned-1", deleted: true, already_absent: false, error_code: null }] });
    render(<ManagePage />);
    await selectMedia(user);
    await user.click(screen.getByRole("button", { name: /delete media/i }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(api.deleteMedia).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /delete permanently/i }));
    expect(api.deleteMedia).toHaveBeenCalledWith({ fileIds: ["owned-1"], urls: [] });
    expect(await screen.findByText("Deleted")).toBeInTheDocument();
  });

  it("explains pending SNS email confirmation", async () => {
    const user = userEvent.setup();
    vi.mocked(api.setNotificationSubscription).mockResolvedValue({ email: "student@example.edu", tags: ["dingo"], status: "PENDING", updated_at: "2026-08-23T00:00:00Z" });
    render(<ManagePage />);
    await user.type(screen.getByLabelText(/watched tags/i), "dingo");
    await user.click(screen.getByRole("button", { name: /start watching/i }));
    expect(api.setNotificationSubscription).toHaveBeenCalledWith(["dingo"]);
    expect(await screen.findByText(/pending confirmation for student@example.edu/i)).toBeInTheDocument();
  });
});
