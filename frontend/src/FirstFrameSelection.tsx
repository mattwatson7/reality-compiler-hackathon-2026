import { useRef, useState } from "react";
import { request } from "./api";
import type { Box, Initialization, Job } from "./types";

type Point = [number, number];
export function normalizedBox(start: Point, end: Point,
  rect: { left: number; top: number; width: number; height: number }): Box | null {
  if (rect.width <= 0 || rect.height <= 0) return null;
  const clamp = (v: number) => Math.min(1, Math.max(0, v));
  const x1 = clamp((start[0] - rect.left) / rect.width);
  const y1 = clamp((start[1] - rect.top) / rect.height);
  const x2 = clamp((end[0] - rect.left) / rect.width);
  const y2 = clamp((end[1] - rect.top) / rect.height);
  const box = { x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) };
  return box.width >= .02 && box.height >= .02 ? box : null;
}

export function FirstFrameSelection({ job, onSubmitted }: { job: Job; onSubmitted: () => void }) {
  const graph = job.graph?.version === "2.0" ? job.graph : null;
  const targets = [
    ...(graph?.objects.map(o => ({ key: `object:${o.id}`, label: o.label })) ?? []),
    ...(graph?.regions.map(r => ({ key: `region:${r.id}`, label: r.description })) ?? []),
  ];
  const [target, setTarget] = useState(targets[0]?.key ?? "");
  const [boxes, setBoxes] = useState<Record<string, Box>>({});
  const [draft, setDraft] = useState<Box | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const start = useRef<Point | null>(null);
  const image = useRef<HTMLImageElement>(null);
  if (!graph || !job.preview_url || !job.frame_reference) return <p>No selectable objects or regions in this program.</p>;

  async function submit() {
    setSending(true); setError(null);
    const body: Initialization = { frame_reference: job.frame_reference!, objects: {}, regions: {} };
    for (const [key, box] of Object.entries(boxes)) {
      const [kind, id] = key.split(":");
      (kind === "object" ? body.objects : body.regions)[id] = box;
    }
    try {
      await request(`/api/jobs/${job.id}/initialize`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      onSubmitted();
    } catch (err) { setError(String(err)); setSending(false); }
  }
  return <section className="selection-panel" aria-label="First-frame selection">
    <h2>Select objects and marked region</h2>
    <p>Draw tight rectangles around each distinct saturated object, then the marked region. Use a fixed camera and plain background. Selection supplies identity, never event times.</p>
    <label>Selection target <select aria-label="Selection target" value={target} disabled={sending}
      onChange={e => setTarget(e.target.value)}>{targets.map(t => <option key={t.key} value={t.key}>{t.label}{boxes[t.key] ? " ✓" : ""}</option>)}</select></label>
    <div className="selection-image" onPointerDown={e => {
      if (sending || !image.current) return;
      start.current = [e.clientX, e.clientY]; e.currentTarget.setPointerCapture?.(e.pointerId);
    }} onPointerMove={e => {
      if (start.current && image.current) setDraft(normalizedBox(start.current, [e.clientX, e.clientY], image.current.getBoundingClientRect()));
    }} onPointerCancel={() => { start.current = null; setDraft(null); }} onPointerUp={e => {
      if (!start.current || !image.current) return;
      const box = normalizedBox(start.current, [e.clientX, e.clientY], image.current.getBoundingClientRect());
      start.current = null; setDraft(null);
      if (box) { setBoxes(previous => ({ ...previous, [target]: box })); setError(null); }
      else setError("Draw a rectangle at least 2% of the image in each dimension.");
    }}>
      <img ref={image} draggable={false} src={job.preview_url} alt="First normalized frame" />
      <svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-label="Selection rectangles">
        {Object.entries({ ...boxes, ...(draft ? { [target]: draft } : {}) }).map(([key, box]) =>
          <rect key={key} {...box} className={key.startsWith("region:") ? "region-box" : "object-box"} />)}
      </svg>
    </div>
    <ul>{targets.map(t => <li key={t.key}>{t.label}: {boxes[t.key] ? "selected" : "required"}</li>)}</ul>
    {error && <p role="alert">{error}</p>}
    <button onClick={() => void submit()} disabled={sending || !targets.length || targets.some(t => !boxes[t.key])}>Start tracking actual frames</button>
    <button className="secondary" disabled={sending} onClick={() => { setBoxes({}); setError(null); }}>Clear selections</button>
  </section>;
}
