import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { formatTime, request } from "./api";
import { EvidenceViewer } from "./EvidenceViewer";
import type { Job } from "./types";

const job: Job = {
  id: "demo",
  status: "completed",
  progress: 100,
  message: "Complete",
  mode: "fixture",
  procedure: "First. Second.",
  expires_at: 9999999999,
  duration_s: 7,
  graph: {
    version: "1.0",
    procedure: "First. Second.",
    objects: [],
    steps: [
      { id: "s1", instruction: "First", object_ids: [] },
      { id: "s2", instruction: "Second", object_ids: [] },
    ],
    constraints: [{ id: "c1", before: "s1", after: "s2" }],
  },
  media_url: "/api/jobs/demo/media",
  error: null,
  result: {
    verdict: "PASS",
    reason: "Order supported",
    steps: [],
    constraints: [
      {
        id: "c1",
        verdict: "PASS",
        reason: "Ordered",
        evidence_ids: ["e1", "e2"],
      },
    ],
    evidence: [
      {
        id: "e1",
        start_s: 1,
        end_s: 1.8,
        description: "Block moves",
        source: "fixture",
      },
      {
        id: "e2",
        start_s: 3,
        end_s: 3.8,
        description: "Cup placed",
        source: "fixture",
      },
    ],
  },
};

describe("evidence review", () => {
  it("maps rounded browser frame timestamps to the correct original frame", () => {
    const mapped = {...job, mode:"local_cv", media_metadata:{width:160,height:120,fps:24,
      normalized_sha256:"normalized",source_timing:{source_time_base:"1/30",source_sha256:"source",
        frames:[0,1,2,3].map(n => ({normalized_index:n,normalized_time_s:n/24,source_index:n,
          source_pts:n,source_time_s:n/30}))}}} as Job;
    render(<EvidenceViewer job={mapped} />);
    const player = screen.getByLabelText("Verification video") as HTMLVideoElement;
    player.currentTime = 0.083333;
    fireEvent.timeUpdate(player);
    fireEvent.click(screen.getByText("Inspect original source frame"));
    fireEvent.click(screen.getByRole("button", {name:"Inspect source at playhead"}));
    expect(screen.getByAltText("Original decoded source frame 2")).toHaveAttribute("src", "/api/jobs/demo/source-frames/2");
  });
  it("seeks the video from timestamped evidence links and the scrubber", () => {
    render(<EvidenceViewer job={job} />);
    const video = screen.getByLabelText(
      "Verification video",
    ) as HTMLVideoElement;
    Object.defineProperty(video, "readyState", { value: 1 });
    fireEvent.click(screen.getByRole("link", { name: /Cup placed/ }));
    expect(video.currentTime).toBe(3);
    fireEvent.change(screen.getByLabelText("Video playhead"), {
      target: { value: "2" },
    });
    expect(video.currentTime).toBe(2);
    expect(screen.getAllByText(/fixture/i).length).toBeGreaterThan(0);
  });

  it("shows UNKNOWN without fabricating evidence and disables expired playback", () => {
    const { rerender } = render(
      <EvidenceViewer
        job={{
          ...job,
          mode: "mock-upload",
          result: {
            verdict: "UNKNOWN",
            reason: "No observations",
            steps: [],
            constraints: [],
            evidence: [],
          },
        }}
      />,
    );
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
    expect(screen.getByText(/No event evidence/)).toBeInTheDocument();
    rerender(
      <EvidenceViewer job={{ ...job, status: "expired", media_url: null }} />,
    );
    expect(screen.getByText(/Media expired/)).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Verification video"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Cup placed/ }),
    ).not.toBeInTheDocument();
  });
});

it("runs a labeled fixture and polls to display its result", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      let body: unknown = {};
      if (url === "/api/fixtures")
        body = [
          {
            id: "correct",
            title: "Correct sequence",
            description: "Synthetic",
            procedure: "First. Second.",
          },
        ];
      else if (url === "/api/costs")
        body = { committed_microusd: 0, cap_microusd: 100000000 };
      else if (url === "/api/jobs/demo/correct") body = { id: "demo" };
      else if (url === "/api/jobs/demo") body = job;
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
  render(<App />);
  expect(screen.getByText(/No live model inference/)).toBeInTheDocument();
  fireEvent.click(
    await screen.findByRole("button", { name: /Correct sequence/ }),
  );
  await waitFor(() =>
    expect(screen.getByText("Order supported")).toBeInTheDocument(),
  );
  expect(screen.getByLabelText("Procedure")).toHaveValue("First. Second.");
  fireEvent.change(screen.getByLabelText("Procedure"), {
    target: { value: "New instructions" },
  });
  expect(screen.getByText("Order supported")).toBeInTheDocument();
});

it("unlocks controls when a job cannot be found", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/jobs/demo/missing-job")
        return new Response('{"detail":"Not found"}', { status: 404 });
      const body =
        url === "/api/fixtures"
          ? [{ id: "correct", title: "Correct sequence", procedure: "First." }]
          : url === "/api/jobs/demo/correct"
            ? { id: "missing-job" }
            : url === "/api/jobs/missing-job"
              ? null
              : { committed_microusd: 0, cap_microusd: 100000000 };
      return body === null
        ? new Response('{"detail":"Not found"}', { status: 404 })
        : new Response(JSON.stringify(body));
    }),
  );
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Correct sequence/ }),
  );
  await screen.findByRole("alert");
  expect(
    screen.getByRole("button", { name: /Correct sequence/ }),
  ).toBeEnabled();
  expect(screen.getByLabelText("Procedure")).toBeEnabled();
});

it("uploads the chosen video and procedure as multipart data", async () => {
  const fetchMock = vi.fn(
    async (url: string) =>
      new Response(
        JSON.stringify(
          url === "/api/fixtures"
            ? []
            : url === "/api/jobs/upload"
              ? { id: "upload" }
              : url === "/api/costs"
                ? { committed_microusd: 0, cap_microusd: 100000000 }
                : job,
        ),
      ),
  );
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  const file = new File(["video"], "demo.mp4", { type: "video/mp4" });
  fireEvent.change(screen.getByLabelText("Upload video"), {
    target: { files: [file] },
  });
  fireEvent.change(screen.getByLabelText("Procedure"), {
    target: { value: "Lift cup." },
  });
  fireEvent.click(
    screen.getByRole("button", { name: /Verify uploaded video/ }),
  );
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([url]) => url === "/api/jobs/upload"),
    ).toBe(true),
  );
  const call = (
    fetchMock.mock.calls as unknown as [string, RequestInit][]
  ).find(([url]) => url === "/api/jobs/upload");
  const form = call?.[1].body as FormData;
  expect(form.get("procedure")).toBe("Lift cup.");
  expect(form.get("video")).toBe(file);
});

it("surfaces server errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response('{"detail":"Queue full"}', { status: 429 })),
  );
  await expect(request("/api/jobs")).rejects.toThrow("Queue full");
});

it("formats timestamps defensively", () => {
  expect(formatTime(63.25)).toBe("01:03.3");
  expect(formatTime(-1)).toBe("00:00.0");
  expect(formatTime(Infinity)).toBe("00:00.0");
});
it("explains the active live pipeline and keeps SAM selectable", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url === "/api/health" ? {
      real_muse_compilation: true,
      real_video_verification: true,
      meta: { paid_inference_enabled: true, sam_selectable: true,
        catalog_authenticated: true, models: ["sam-3.1", "muse-wonder-1.0"],
        reason: "Fresh account catalog verified; paid dispatch is enabled" }
    } : url === "/api/fixtures" ? [] : { committed_microusd: 0, cap_microusd: 100000000 }
  ))));
  render(<App />);
  expect(await screen.findByText("META SAM / LOCAL CV")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Compile TaskGraph · paid Wonder/ })).toBeInTheDocument();
  expect(screen.getByText(/The local rules compiler supports/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Upload perception"), { target: { value: "meta_sam" } });
  expect(screen.getByText(/Muse Wonder interprets your instructions/)).toBeInTheDocument();
  expect(screen.getByRole("option", { name: /Meta SAM/ })).toBeEnabled();
  expect(screen.getByText(/Upload to compile once/)).toBeInTheDocument();
});
