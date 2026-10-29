import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { App } from "./App";
import { EvidenceViewer } from "./EvidenceViewer";
import type { Job } from "./types";

const source = { start: 0, end: 8, quote: "See cup." };
const semanticGraph = {
  version: "2.0", procedure: "See cup.", compilation_source: "muse",
  objects: [{ id: "cup", label: "Cup", description: "Blue ceramic cup", grounding_prompt: "Track the blue cup" }],
  regions: [{ id: "mat", description: "Mat area", grounding_prompt: "Visible mat boundary", coordinate_semantics: "visible_image_region", observability: "AMBIGUOUS", reason: "Mat boundary is unclear" }],
  events: [
    { id: "enter", instruction: "Move cup into mat", source, required: true, observability: "SUPPORTED", reason: null, predicate: { type: "object_entered_region", object_id: "cup", region_id: "mat" } },
    { id: "change", instruction: "Open cup lid", source, required: false, observability: "SUPPORTED", reason: null, predicate: { type: "visually_confirmed_state_change", object_id: "cup", state_dimension: "lid position", from_state: "closed", to_state: "open", visual_criteria: "Lid visibly raised" } },
    { id: "see", instruction: "See cup", source, required: true, observability: "SUPPORTED", reason: null, predicate: { type: "object_visible", object_id: "cup" } },
  ],
  constraints: [{ id: "order", operator: "AFTER", first: "see", second: "enter", source }],
  conditions: [
    { id: "sterile", instruction: "Keep cup sterile", source, predicate: null, required: true, observability: "UNSUPPORTED", reason: "Sterility is not visually observable", scope: "during" },
    { id: "final", instruction: "Cup remains visible at clip end", source, predicate: { type: "object_visible", object_id: "cup" }, required: true, observability: "SUPPORTED", reason: null, scope: "final" },
  ],
};

function mockCompile(graph: unknown) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url === "/api/fixtures" ? [] : url === "/api/compile" ? graph : url === "/api/health" ? {
      compiler_source: "fixture", real_muse_compilation: false, real_video_verification: false, live_inference: false,
    } : { committed_microusd: 0, cap_microusd: 100000000 },
  ))));
}

it("renders semantic objects, predicate arguments, observability and final conditions", async () => {
  mockCompile(semanticGraph);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /Compile TaskGraph/ }));
  const program = await screen.findByLabelText("Compiled program");
  expect(within(program).getByText("Blue ceramic cup")).toBeInTheDocument();
  expect(within(program).getByText("Track the blue cup")).toBeInTheDocument();
  expect(within(program).getByText("Mat boundary is unclear")).toBeInTheDocument();
  expect(within(program).getByText("object_entered_region")).toBeInTheDocument();
  expect(within(program).getByText("lid position: closed → open")).toBeInTheDocument();
  expect(within(program).getByText("Lid visibly raised")).toBeInTheDocument();
  expect(within(program).getByText("Sterility is not visually observable")).toBeInTheDocument();
  expect(within(program).getByRole("heading", { name: "Final states" })).toBeInTheDocument();
  expect(within(program).getByText("Optional")).toBeInTheDocument();
  expect(within(program).getByText("Compilation source: muse")).toBeInTheDocument();
  expect(within(program).getByText("see AFTER enter")).toBeInTheDocument();
  expect(program.querySelectorAll(".graph-arrow")).toHaveLength(0);
});

it("preserves legacy graphs without inventing edges between adjacent steps", async () => {
  mockCompile({ version: "1.0", procedure: "First. Second.", objects: [], steps: [
    { id: "s1", instruction: "First", object_ids: [] }, { id: "s2", instruction: "Second", object_ids: [] },
  ], constraints: [] });
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /Compile TaskGraph/ }));
  const program = await screen.findByLabelText("Compiled program");
  expect(within(program).getByText("First")).toBeInTheDocument();
  expect(within(program).getByText(/No temporal constraints/)).toBeInTheDocument();
  expect(program.querySelectorAll(".graph-arrow")).toHaveLength(0);
});

it("separately labels inactive real compilation and video verification", async () => {
  mockCompile(semanticGraph);
  render(<App />);
  expect(await screen.findByText("Real Muse compilation: inactive")).toBeInTheDocument();
  expect(screen.getByText("Real video verification: inactive")).toBeInTheDocument();
});

it("shows v2 conditions and optional checks while keeping Muse-compiled mock uploads UNKNOWN", () => {
  const job = {
    id: "upload", status: "completed", progress: 100, message: "Complete", mode: "mock-upload", procedure: "See cup.",
    expires_at: 9999999999, duration_s: 7, graph: semanticGraph, media_url: "/api/jobs/upload/media", error: null,
    result: { verdict: "UNKNOWN", reason: "Mock perception has no observations", steps: [
      { id: "change", verdict: "UNKNOWN", reason: "Optional event absent", evidence_ids: [], required: false },
    ], constraints: [{ id: "order", verdict: "UNKNOWN", reason: "No event observations", evidence_ids: [], required: true }],
    conditions: [{ id: "final", verdict: "UNKNOWN", reason: "No end-of-clip evidence", evidence_ids: [], required: true }], evidence: [] },
  } as Job;
  render(<EvidenceViewer job={job} />);
  expect(screen.getByText("Mock perception has no observations")).toBeInTheDocument();
  expect(screen.getByText("see AFTER enter")).toBeInTheDocument();
  expect(screen.getByText("Cup remains visible at clip end (final)")).toBeInTheDocument();
  expect(screen.getByText("Optional")).toBeInTheDocument();
  expect(screen.getByText("No end-of-clip evidence")).toBeInTheDocument();
});
