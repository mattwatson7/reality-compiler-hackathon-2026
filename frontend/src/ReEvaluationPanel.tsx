import { useEffect, useState } from "react";
import { formatTime, request } from "./api";
import { Badge } from "./EvidenceViewer";
import { ProgramView } from "./ProgramView";
import type { EvaluationSnapshot, Job, TaskGraph } from "./types";

function requirementLabel(graph: TaskGraph, id: string): string {
  if (graph.version !== "2.0") return id;
  const requirement = [...graph.events, ...graph.conditions].find(item => item.id === id);
  const predicate = requirement?.predicate;
  if (predicate) {
    const object = graph.objects.find(item => item.id === predicate.object_id)?.label ?? predicate.object_id;
    if (predicate.type === "object_visible") return `${object} visible`;
    if ("region_id" in predicate) return `${object} ${predicate.type === "object_entered_region" ? "enters" : "exits"} selected region`;
    return `${object}: ${predicate.from_state} → ${predicate.to_state}`;
  }
  if (requirement) return requirement.instruction;
  const constraint = graph.constraints.find(item => item.id === id);
  return constraint ? `${requirementLabel(graph, constraint.first)} ${constraint.operator.toLowerCase()} ${requirementLabel(graph, constraint.second)}` : id;
}

export function ReEvaluationPanel({ job, paidCompiler = false }: { job: Job; paidCompiler?: boolean }) {
  const [draft, setDraft] = useState(job.procedure);
  const [history, setHistory] = useState<EvaluationSnapshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    request<EvaluationSnapshot[]>(`/api/jobs/${job.id}/evaluations`, { signal: controller.signal })
      .then(items => { if (!controller.signal.aborted) { setHistory(items); setRight(Math.max(0, items.length - 1)); } })
      .catch(err => { if (!controller.signal.aborted) setError(String(err)); });
    return () => controller.abort();
  }, [job.id]);

  async function evaluate() {
    setBusy(true);
    setError(null);
    try {
      const item = await request<EvaluationSnapshot>(`/api/jobs/${job.id}/evaluations`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ procedure: draft }),
      });
      setHistory(previous => [...previous, item]);
      setRight(history.length);
    } catch (err) { setError(String(err)); }
    finally { setBusy(false); }
  }

  function card(item: EvaluationSnapshot, index: number) {
    return <article className="comparison-card" key={`${item.id}-${index}`}>
      <div className="check-heading"><Badge verdict={item.result.verdict} /><strong>Evaluation {index + 1}</strong></div>
      <p className="comparison-procedure">{item.procedure}</p>
      <p>{item.result.reason}</p>
      <p className="field-help provider-provenance">Compiler: {item.provenance.compiler} · Tracker: {item.provenance.tracker}<br />Observer: {item.provenance.observer}</p>
      <p className="field-help">{item.reuse_status === "original" ? "Original analysis" : item.reuse_status === "reused" ? "Same visual evidence · no new perception · SAM and Spark not called again" : "New analysis needed"}</p>
      {item.reuse_reasons.map((reason, i) => <p key={i} className="notice">{reason} Upload again and select the required objects and regions.</p>)}
      <ul className="comparison-checks">{[...item.result.steps, ...item.result.constraints, ...(item.result.conditions ?? [])].map(check =>
        <li key={check.id}><Badge verdict={check.verdict} /> <strong>{requirementLabel(item.graph, check.id)}: </strong>{check.reason}</li>
      )}</ul>
      <div className="evidence-links">{item.result.evidence.map(evidence => <a key={evidence.id} href="#verification-video" onClick={() => {
        document.getElementById("verification-video")?.dispatchEvent(new CustomEvent("evidence-seek", {detail:evidence.start_s}));
      }}>{formatTime(evidence.start_s)}–{formatTime(evidence.end_s)} · {evidence.description}</a>)}</div>
      <details><summary>Verification program and provenance</summary>
        <ProgramView graph={item.graph} />
        <p className="fingerprint">Evidence identity: {item.evidence_fingerprint}</p>
      </details>
    </article>;
  }

  return <section className="reevaluation panel" aria-label="Compare procedures">
    <div className="section-heading"><div><span className="eyebrow">04 / RE-EVALUATE</span><h2>One recording. Different requirements.</h2></div></div>
    <p>Change what should happen. Keep the original analysis and compare independent verdicts against the same evidence.</p>
    <label htmlFor="revised-procedure">Revised procedure</label>
    <textarea id="revised-procedure" rows={3} maxLength={10000} value={draft} disabled={busy || job.status === "expired"} onChange={e => setDraft(e.target.value)} />
    <p className="field-help">Objects and region definitions must match the original selection. New requirements may need another analysis. {job.mode === "meta_sam" && paidCompiler && job.execution_mode !== "offline_capture_review" ? "Muse Wonder compiles revisions · paid." : "Local compilation · no paid calls."}</p>
    <button className="primary" disabled={busy || history.length === 0 || !draft.trim() || job.status !== "completed" || history.length >= 51} onClick={() => void evaluate()}>{busy ? "Evaluating…" : "Evaluate same evidence"}</button>
    {job.status === "expired" && <p className="notice">Media expired. Evaluation history remains available.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {history.length > 0 && <>
      <div className="comparison-selectors">
        <label>Compare <select aria-label="First evaluation" value={left} onChange={e => setLeft(Number(e.target.value))}>{history.map((item, i) => <option key={item.id} value={i}>Evaluation {i + 1} · {item.result.verdict}</option>)}</select></label>
        <label>With <select aria-label="Second evaluation" value={right} onChange={e => setRight(Number(e.target.value))}>{history.map((item, i) => <option key={item.id} value={i}>Evaluation {i + 1} · {item.result.verdict}</option>)}</select></label>
      </div>
      {right !== left && history[left].evidence_fingerprint && history[left].evidence_fingerprint === history[right].evidence_fingerprint && history[right].reuse_status === "reused" && <aside className="reuse-proof" aria-label="Evidence reuse verified">
        <strong>Same perception fingerprint · independently evaluated requirements</strong>
        <p>No new perception for this revision. Inspect each compiler, tracker and observer below.</p>
        <p className="fingerprint">{history[left].evidence_fingerprint}</p>
      </aside>}
      <div className="comparison-grid">{card(history[left], left)}{right !== left && card(history[right], right)}</div>
    </>}
  </section>;
}
