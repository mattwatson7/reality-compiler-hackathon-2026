import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { FirstFrameSelection, normalizedBox } from "./FirstFrameSelection";
import { TrackingOverlay } from "./TrackingOverlay";
import type { Job } from "./types";
import { App } from "./App";

it("keeps Meta SAM disabled until backend confirms paid configuration and entitlement", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url === '/api/fixtures' ? [] : url === '/api/health' ? {
      compiler_source: 'local_rules', real_muse_compilation: false, real_video_verification: true,
      meta: { catalog_authenticated: true, models: ['sam-3.1'], paid_inference_enabled: false,
        sam_selectable: false, reason: 'Explicit paid authorization required' },
    } : { committed_microusd: 0, cap_microusd: 100000000 }
  ))));
  render(<App />);
  await screen.findByLabelText('Meta integration status');
  expect(screen.getByRole('option', { name: /Meta SAM/ })).toBeDisabled();
  expect(screen.getByRole('option', { name: /Local OpenCV/ })).toBeEnabled();
  expect(screen.getByRole('option', { name: /Fixture Demo/ })).toBeEnabled();
});

it("maps rectangles within the displayed image and rejects tiny selections", () => {
  expect(normalizedBox([100, 50], [200, 100], { left: 0, top: 0, width: 400, height: 200 })).toEqual(
    { x: .25, y: .25, width: .25, height: .25 });
  expect(normalizedBox([0, 0], [1, 1], { left: 0, top: 0, width: 400, height: 200 })).toBeNull();
});

const pending = {
  id: "local", status: "awaiting_initialization", mode: "local_cv", frame_reference: "sha:0",
  preview_url: "/api/jobs/local/frames/0", graph: {
    version: "2.0", objects: [{ id: "block", label: "blue block" }, { id: "cup", label: "cup" }],
    regions: [{ id: "region", description: "Marked region" }],
  },
} as Job;

it("requires all selections and binds submission to immutable first frame", () => {
  render(<FirstFrameSelection job={pending} onSubmitted={vi.fn()} />);
  expect(screen.getByRole("img", { name: "First normalized frame" })).toHaveAttribute("src", pending.preview_url);
  expect(screen.getByRole("button", { name: /Start tracking/ })).toBeDisabled();
  expect(screen.getByLabelText("Selection target")).toHaveTextContent("blue block");
  fireEvent.change(screen.getByLabelText("Selection target"), { target: { value: "object:cup" } });
  expect(screen.getByLabelText("Selection target")).toHaveValue("object:cup");
});

it("submits drawn boxes once with first-frame identity and no event times", async () => {
  vi.stubGlobal("PointerEvent", MouseEvent);
  const onSubmitted = vi.fn();
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: pending.id })));
  vi.stubGlobal("fetch", fetchMock);
  render(<FirstFrameSelection job={pending} onSubmitted={onSubmitted} />);
  const image = screen.getByRole("img", { name: "First normalized frame" });
  vi.spyOn(image, "getBoundingClientRect").mockReturnValue({ x: 0, y: 0, left: 0, top: 0, right: 400, bottom: 200, width: 400, height: 200, toJSON: () => ({}) });
  const stage = image.parentElement!;
  for (const [target, start, end] of [
    ["object:block", [20, 20], [60, 60]],
    ["object:cup", [20, 100], [60, 140]],
    ["region:region", [220, 10], [380, 180]],
  ] as const) {
    fireEvent.change(screen.getByLabelText("Selection target"), { target: { value: target } });
    fireEvent.pointerDown(stage, { clientX: start[0], clientY: start[1], pointerId: 1 });
    fireEvent.pointerMove(stage, { clientX: end[0], clientY: end[1], pointerId: 1 });
    fireEvent.pointerUp(stage, { clientX: end[0], clientY: end[1], pointerId: 1 });
  }
  const submit = screen.getByRole("button", { name: /Start tracking/ });
  expect(submit).toBeEnabled();
  fireEvent.click(submit);
  expect(submit).toBeDisabled();
  await waitFor(() => expect(onSubmitted).toHaveBeenCalledOnce());
  const [url, options] = (fetchMock.mock.calls as unknown as [string, RequestInit][])[0];
  expect(url).toBe("/api/jobs/local/initialize");
  const body = JSON.parse(options.body as string);
  expect(Object.keys(body).sort()).toEqual(["frame_reference", "objects", "regions"]);
  expect(body.frame_reference).toBe("sha:0");
  expect(body.objects.block.x).toBeCloseTo(.05);
  expect(body.objects.block.y).toBeCloseTo(.1);
  expect(body.objects.block.width).toBeCloseTo(.1);
  expect(body.objects.block.height).toBeCloseTo(.2);
});

it("shows only reliable nearby samples and removes overlays during loss or expiration", () => {
  const tracked = { ...pending, status: "completed", initialization: {
    frame_reference: "sha:0", objects: {}, regions: { region: { x: .5, y: .5, width: .4, height: .4 } },
  }, tracks: [{ object_id: "block", source: "local_cv", diagnostics: [], invalid_intervals: [],
    provenance: "local", samples: [
      { time_s: 0, frame_index: 0, box: { x: .1, y: .1, width: .1, height: .1 }, status: "reliable", confidence: .9, contour: [], quality_components: {}, region_overlap: {} },
      { time_s: .0833, frame_index: 2, box: null, status: "missing", confidence: 0, contour: [], quality_components: {}, region_overlap: {} },
    ] }] } as Job;
  const { rerender } = render(<TrackingOverlay job={tracked} time={0} />);
  expect(screen.getByLabelText("Tracked block")).toBeInTheDocument();
  rerender(<TrackingOverlay job={tracked} time={.0833} />);
  expect(screen.queryByLabelText("Tracked block")).not.toBeInTheDocument();
  rerender(<TrackingOverlay job={{ ...tracked, status: "expired" }} time={0} />);
  expect(screen.queryByLabelText("Tracking overlay")).not.toBeInTheDocument();
});
