import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MediaRecord } from "../api/types";
import * as api from "../api/client";
import * as temporary from "../queries/temporaryQueryWorkflow";
import { SearchPage } from "./SearchPage";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, lookupThumbnail: vi.fn(), queryRequirements: vi.fn(), querySpecies: vi.fn() };
});
vi.mock("../queries/temporaryQueryWorkflow", async () => {
  const actual = await vi.importActual<typeof import("../queries/temporaryQueryWorkflow")>("../queries/temporaryQueryWorkflow");
  return { ...actual, runTemporaryQuery: vi.fn() };
});

const media: MediaRecord = {
  file_id: "ready-1", filename: "wombat.jpg", file_type: "image",
  species_counts: { wombat: 2, dingo: 1 }, auto_tags: ["dingo", "wombat"], manual_tags: [], all_tags: ["dingo", "wombat"],
  processing_status: "READY", error_code: null, detections: [], model_version: "supplied-v1", video_samples: null,
  thumbnail_url: "https://example.test/thumb", original_url: "https://example.test/full", created_at: "2026-08-23T00:00:00Z", updated_at: "2026-08-23T00:00:00Z", version: 3,
};

describe("query UI", () => {
  beforeEach(() => {
    vi.mocked(api.queryRequirements).mockResolvedValue({ media: [media], total: 1, truncated: false });
    vi.mocked(api.querySpecies).mockResolvedValue({ media: [], total: 0, truncated: false });
  });

  it("sends normalized minimum-count AND requirements", async () => {
    const user = userEvent.setup();
    render(<SearchPage />);
    await user.type(screen.getByLabelText(/species or tag 1/i), "Wombat");
    await user.clear(screen.getByLabelText("Minimum"));
    await user.type(screen.getByLabelText("Minimum"), "2");
    await user.click(screen.getByRole("button", { name: /add requirement/i }));
    await user.type(screen.getByLabelText(/species or tag 2/i), "Dingo");
    await user.click(screen.getByRole("button", { name: /search counts/i }));
    expect(api.queryRequirements).toHaveBeenCalledWith({ wombat: 2, dingo: 1 });
    expect(await screen.findByRole("heading", { name: "1 record" })).toBeInTheDocument();
  });

  it("shows an honest empty species result", async () => {
    const user = userEvent.setup();
    render(<SearchPage />);
    await user.click(screen.getByRole("tab", { name: /species one tag/i }));
    await user.type(screen.getByLabelText(/species or tag/i), "koala");
    await user.click(screen.getByRole("button", { name: /search species/i }));
    expect(await screen.findByRole("heading", { name: /no matching wildlife/i })).toBeInTheDocument();
  });

  it("recovers the original from a thumbnail reference", async () => {
    const user = userEvent.setup();
    vi.mocked(api.lookupThumbnail).mockResolvedValue({ file_id: "ready-1", original_url: "https://example.test/full" });
    render(<SearchPage />);
    await user.click(screen.getByRole("tab", { name: /thumbnail find original/i }));
    await user.type(screen.getByLabelText(/thumbnail url or key/i), "thumbnails/ready-1.jpg");
    await user.click(screen.getByRole("button", { name: /find original/i }));
    const openOriginal = await screen.findByRole("button", { name: /open original/i });
    expect(openOriginal.tagName).toBe("BUTTON");
    await user.click(openOriginal);
    expect(screen.getByRole("dialog", { name: /file ready-1/i })).toBeInTheDocument();
    const preview = screen.getByRole("img", { name: /original preview/i });
    expect(preview).toHaveAttribute("src", "https://example.test/full");
    await user.click(preview);
    expect(screen.getByRole("dialog", { name: /file ready-1/i })).toBeInTheDocument();
  });

  it("runs a temporary image query and displays detected counts", async () => {
    const user = userEvent.setup();
    vi.mocked(temporary.runTemporaryQuery).mockResolvedValue({ query_id: "query-1", processing_status: "READY", media: [media], total: 1, truncated: false, detected_species_counts: { dingo: 1 }, model_version: "supplied-v1" });
    render(<SearchPage />);
    await user.click(screen.getByRole("tab", { name: /image visual query/i }));
    const file = new File(["query"], "query.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/choose jpg/i), file);
    await user.click(screen.getByRole("button", { name: /analyse and search/i }));
    expect(temporary.runTemporaryQuery).toHaveBeenCalledWith(file, expect.any(Function));
    expect(await screen.findByText(/query image detected/i)).toBeInTheDocument();
    expect(screen.getByText("dingo", { selector: ".detected-summary dt" })).toBeInTheDocument();
  });
});
