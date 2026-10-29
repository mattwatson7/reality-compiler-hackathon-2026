import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ReEvaluationPanel } from "./ReEvaluationPanel";
import { EvidenceViewer } from "./EvidenceViewer";
import type { Job } from "./types";

it("prevents submission while the initial history snapshot is pending", () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
  render(<ReEvaluationPanel job={{id:"pending",status:"completed",procedure:"Original"} as Job} />);
  fireEvent.change(screen.getByLabelText("Revised procedure"), {target:{value:"Revised"}});
  expect(screen.getByRole("button", {name:"Evaluate same evidence"})).toBeDisabled();
});

it("seeks the evidence player from a comparison result", async () => {
  const result = {verdict:"PASS", reason:"Supported", steps:[], constraints:[], evidence:[
    {id:"entry", start_s:2.25, end_s:2.5, description:"Cup entry", source:"fixture"},
  ]};
  const snapshot = {id:"original", procedure:"Original", graph:{version:"1.0",procedure:"Original",objects:[],steps:[],constraints:[]}, result,
    reuse_status:"original", reuse_reasons:[], provenance:{}, evidence_fingerprint:"hash"};
  vi.stubGlobal("fetch", vi.fn(async () => ({ok:true, json:async () => [snapshot]})));
  const job = {id:"run",status:"completed",procedure:"Original",mode:"fixture",media_url:"/video",
    duration_s:4,expires_at:9999999999,result:null} as Job;
  render(<><EvidenceViewer job={job} /><ReEvaluationPanel job={job} /></>);
  const player = screen.getByLabelText("Verification video") as HTMLVideoElement;
  Object.defineProperty(player, "readyState", {value:1});
  fireEvent.click(await screen.findByRole("link", {name:/Cup entry/}));
  expect(player.currentTime).toBe(2.25);
});

it("keeps original analysis while adding independent procedure results", async () => {
  const original = { id: "original", procedure: "Observed order", graph: {
    version: "1.0", procedure: "Observed order", objects: [], steps: [], constraints: [],
  },
    result: { verdict: "PASS", reason: "Supported", steps: [], constraints: [], evidence: [] },
    reuse_status: "original", reuse_reasons: [], provenance: {}, evidence_fingerprint: "hash" };
  const revised = { ...original, id: "revised", procedure: "Reverse order", reuse_status: "reused",
    result: { ...original.result, verdict: "FAIL", reason: "Reverse order proven" } };
  const fetcher = vi.fn(async (_url: string, options?: RequestInit) => ({ ok: true,
    json: async () => options?.method === "POST" ? revised : [original] }));
  vi.stubGlobal("fetch", fetcher);
  render(<ReEvaluationPanel job={{ id: "run", status: "completed", procedure: original.procedure } as Job} />);
  await screen.findByText("PASS");
  fireEvent.change(screen.getByLabelText("Revised procedure"), { target: { value: "Reverse order" } });
  fireEvent.click(screen.getByRole("button", { name: /Evaluate same evidence/ }));
  await screen.findByText("FAIL");
  expect(screen.getByText("PASS")).toBeInTheDocument();
  expect(screen.getByText("Reverse order proven")).toBeInTheDocument();
  expect(screen.getByLabelText("Evidence reuse verified")).toHaveTextContent("hash");
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith("/api/jobs/run/evaluations", expect.objectContaining({
    method: "POST", body: JSON.stringify({ procedure: "Reverse order" }),
  })));
});

it.each([['different-hash', 'reused'], ['same-hash', 'requires_new_analysis']])(
  "does not claim verified reuse for fingerprint %s and status %s", async (fingerprint, status) => {
    const original = {id:'first', procedure:'Original', graph:{version:'1.0', procedure:'Original', objects:[], steps:[], constraints:[]},
      result:{verdict:'PASS',reason:'Supported',steps:[],constraints:[],evidence:[]}, reuse_status:'original',reuse_reasons:[],provenance:{},evidence_fingerprint:'same-hash'};
    const revision = {...original,id:'second',reuse_status:status,evidence_fingerprint:fingerprint};
    vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>[original,revision]})));
    render(<ReEvaluationPanel job={{id:'run',status:'completed',procedure:'Original'} as Job} />);
    await screen.findByText('Evaluation 2');
    expect(screen.queryByLabelText('Evidence reuse verified')).not.toBeInTheDocument();
  }
);
