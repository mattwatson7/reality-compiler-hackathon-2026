import type { Job, VisualSample } from "./types";

export function sampleAt(samples: VisualSample[], time: number): VisualSample | undefined {
  // Display the sampled frame only within its own display interval. Never bridge loss.
  const sample = [...samples].reverse().find(s => s.time_s <= time + .000001);
  return sample && sample.status === "reliable" && sample.box && time - sample.time_s < 1 / 24
    ? sample : undefined;
}

export function TrackingOverlay({ job, time }: { job: Job; time: number }) {
  if (!["local_cv", "meta_sam"].includes(job.mode) || job.status === "expired") return null;
  return <svg className="tracking-overlay" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label="Tracking overlay">
    {Object.entries(job.initialization?.regions ?? {}).map(([id, b]) => <g key={id}>
      <rect x={b.x * 1000} y={b.y * 1000} width={b.width * 1000} height={b.height * 1000} className="region-box" />
      <text x={b.x * 1000} y={b.y * 1000 + 30}>{id}</text>
    </g>)}
    {job.tracks?.filter(t => ["local_cv", "meta_sam"].includes(t.source)).map(track => {
      const sample = sampleAt(track.samples, time); const b = sample?.box;
      return b && <g key={track.object_id} aria-label={`Tracked ${track.object_id}`}>
        <rect x={b.x * 1000} y={b.y * 1000} width={b.width * 1000} height={b.height * 1000} className="object-box" />
        {sample.contour.length > 0 && <polygon points={sample.contour.map(([x, y]) => `${x * 1000},${y * 1000}`).join(" ")} className="object-box" />}
        <text x={b.x * 1000} y={Math.max(28, b.y * 1000 - 8)}>{track.object_id} · frame {sample.frame_index} · {sample.confidence.toFixed(2)}</text>
      </g>;
    })}
  </svg>;
}
