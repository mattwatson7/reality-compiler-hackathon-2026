import { useCallback, useEffect, useRef, useState } from "react";
import { formatTime } from "./api";
import { constraintLabel } from "./types";
import type { CheckResult, Evidence, Job, Verdict } from "./types";
import { TrackingOverlay } from "./TrackingOverlay";

export function Badge({ verdict }: { verdict: Verdict }) {
  return <span className={`badge ${verdict.toLowerCase()}`}>{verdict}</span>;
}

export function EvidenceViewer({ job }: { job: Job }) {
  const video = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const [playhead, setPlayhead] = useState(0);
  const [sourceInspection, setSourceInspection] = useState<number | null>(null);
  const result = job.result;
  const duration = job.duration_s ?? 0;
  const available = job.media_url !== null && job.status !== "expired";
  useEffect(() => {
    const player = video.current;
    if (!player?.requestVideoFrameCallback || !["local_cv", "meta_sam"].includes(job.mode)) return;
    let handle = 0;
    function update(_: number, metadata: VideoFrameCallbackMetadata) {
      setPlayhead(metadata.mediaTime);
      handle = player!.requestVideoFrameCallback(update);
    }
    handle = player.requestVideoFrameCallback(update);
    return () => player.cancelVideoFrameCallback(handle);
  }, [job.id, job.mode, available]);
  const evidence = [...(result?.evidence ?? [])].sort(
    (a, b) => a.start_s - b.start_s,
  );

  const seek = useCallback((time: number) => {
    const clamped = Math.min(duration, Math.max(0, time));
    setPlayhead(clamped);
    if (video.current && video.current.readyState >= 1)
      video.current.currentTime = clamped;
    else pendingSeek.current = clamped;
  }, [duration]);

  useEffect(() => {
    const shell = document.getElementById("verification-video");
    const handler = (event: Event) => seek((event as CustomEvent<number>).detail);
    shell?.addEventListener("evidence-seek", handler);
    return () => shell?.removeEventListener("evidence-seek", handler);
  }, [seek, available]);

  const sourceTiming = job.media_metadata?.source_timing;
  // Browsers may round presentation timestamps to microseconds (2/24 -> .083333).
  const sourceIndex = sourceTiming ? Math.min(sourceTiming.frames.length - 1, Math.floor((playhead + 1e-6) * 24)) : 0;
  const sourceFrame = sourceTiming?.frames[sourceInspection ?? sourceIndex];

  function evidenceLink(item: Evidence, compact = false) {
    const label = `${formatTime(item.start_s)}–${formatTime(item.end_s)} ${compact ? item.id : item.description}`;
    return available ? (
      <a
        key={item.id}
        href="#verification-video"
        onClick={() => seek(item.start_s)}
      >
        {label}
        <span aria-hidden="true"> ↗</span>
      </a>
    ) : (
      <span key={item.id}>{label} (media unavailable)</span>
    );
  }

  function checkRow(check: CheckResult, label: string) {
    return (
      <li key={check.id} className="check-row">
        <div className="check-heading">
          <Badge verdict={check.verdict} />
          <strong>{label}</strong>
          <small>{check.required === false ? "Optional" : "Required"}</small>
        </div>
        <p>{check.reason}</p>
        <div className="evidence-links">
          {check.evidence_ids.map((id) => {
            const item = evidence.find((entry) => entry.id === id);
            return item ? evidenceLink(item, true) : null;
          })}
        </div>
      </li>
    );
  }

  return (
    <section className="review" aria-label="Evidence review">
      <div className="section-heading">
        <div>
          <span className="eyebrow">02 / OBSERVE</span>
          <h2>Evidence monitor</h2>
        </div>
        <span className="mono subtle">
          {job.mode === "fixture" ? "SYNTHETIC FIXTURE" : job.mode === "meta_sam" ? "ACTUAL FRAMES / META SAM" : job.mode === "local_cv" ? "ACTUAL FRAMES / LOCAL CV / SAM NOT USED" : "MOCK UPLOAD"}
        </span>
      </div>
      <div className="video-shell" id="verification-video">
        {available ? (
          <div className="video-stage" style={job.media_metadata ? { aspectRatio: `${job.media_metadata.width}/${job.media_metadata.height}` } : undefined}>
          <video
            key={job.media_url}
            ref={video}
            src={job.media_url ?? undefined}
            aria-label="Verification video"
            controls
            playsInline
            preload="metadata"
            onTimeUpdate={() => setPlayhead(video.current?.currentTime ?? 0)}
            onSeeked={() => setPlayhead(video.current?.currentTime ?? 0)}
            onLoadedMetadata={() => {
              if (video.current && pendingSeek.current !== null) {
                video.current.currentTime = pendingSeek.current;
                pendingSeek.current = null;
              }
            }}
          />
          <TrackingOverlay job={job} time={playhead} />
          </div>
        ) : (
          <div className="empty-monitor">
            {job.status === "expired"
              ? "Media expired. Run again to review evidence."
              : "Preparing video…"}
          </div>
        )}
        <span className="video-label">
          {job.execution_mode === "offline_capture_review" && "OFFLINE CAPTURE REVIEW / "}
          {job.mode !== "fixture" && (job.footage_origin === "genuine_camera" ? "CAMERA · USER DECLARED / " : job.footage_origin === "generated" ? "GENERATED · USER DECLARED / " : "SOURCE UNSPECIFIED / ")}
          {job.mode === "fixture"
            ? "FIXTURE / SIMULATED"
            : job.mode === "meta_sam" ? "USER VIDEO / META SAM 3.1" : job.mode === "local_cv" ? "USER VIDEO / LOCAL OPENCV / NO SAM" : "USER VIDEO / NO LIVE INFERENCE"}
        </span>
      </div>
      {sourceTiming && available ? <details className="source-attribution">
        <summary>Inspect original source frame</summary>
        <p>Evidence uses normalized time at 24 fps. The decoder map identifies the original frame, including duplicated or dropped frames. Earlier edits to the uploaded file are unknown.</p>
        <button onClick={() => setSourceInspection(sourceIndex)}>Inspect source at playhead</button>
        {sourceFrame && <p>Normalized frame {sourceFrame.normalized_index} ({sourceFrame.normalized_time_s.toFixed(3)}s) → original decoded frame {sourceFrame.source_index}, PTS {sourceFrame.source_pts} × {sourceTiming.source_time_base} ({sourceFrame.source_time_s.toFixed(6)}s).</p>}
        {sourceInspection !== null && <a href={`/api/jobs/${job.id}/source-frames/${sourceInspection}`} target="_blank" rel="noreferrer"><img className="source-frame" src={`/api/jobs/${job.id}/source-frames/${sourceInspection}`} alt={`Original decoded source frame ${sourceFrame?.source_index}`} /></a>}
        <p className="fingerprint">Source SHA-256: {sourceTiming.source_sha256}</p>
      </details> : job.mode !== "fixture" && <p className="field-help">Legacy source mapping unavailable. Evidence times refer to the normalized recording; exact original frame attribution is not established.</p>}
      {duration > 0 && (
        <div className="timeline">
          <div className="timeline-heading">
            <span className="eyebrow">EVENT TIMELINE</span>
            <span className="mono">
              {formatTime(playhead)}{" "}
              <span className="subtle">/ {formatTime(duration)}</span>
            </span>
          </div>
          <div className="timeline-track" aria-label="Evidence timeline">
            {evidence.map((item) => (
              <button
                key={item.id}
                title={item.description}
                aria-label={`Seek to ${item.description}`}
                disabled={!available}
                style={{
                  left: `${(100 * item.start_s) / duration}%`,
                  width: `${Math.max(2, (100 * (item.end_s - item.start_s)) / duration)}%`,
                }}
                onClick={() => seek(item.start_s)}
              >
                {item.id}
              </button>
            ))}
            <div
              className="playhead"
              style={{ left: `${(100 * playhead) / duration}%` }}
            />
          </div>
          <input
            aria-label="Video playhead"
            type="range"
            min="0"
            max={duration}
            step="0.05"
            value={playhead}
            disabled={!available}
            onChange={(event) => seek(Number(event.target.value))}
          />
          <div className="timeline-scale mono">
            <span>00:00</span>
            <span>{formatTime(duration / 2)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}
      {result && (
        <>
          <div className={`verdict-panel ${result.verdict.toLowerCase()}`}>
            <Badge verdict={result.verdict} />
            <p>{result.reason}</p>
          </div>
          {evidence.length > 0 ? (
            <div className="evidence-list">
              <h3>Supporting evidence</h3>
              {evidence.map((item) => (
                <div key={item.id} className="evidence-item">
                  <span className="event-dot" />
                  {evidenceLink(item)}
                  <small>{item.source}{item.model_id ? ` · ${item.model_id}` : ""}</small>
                  {available && item.frame_indices && <details><summary>Saved supporting frames ({item.frame_indices.length})</summary>
                    <div className="supporting-frames">{item.frame_indices.map(index => <a key={index} href={`/api/jobs/${job.id}/frames/${index}`} target="_blank" rel="noreferrer">
                      <img loading="lazy" src={`/api/jobs/${job.id}/frames/${index}`} alt={`Evidence ${item.id} frame ${index}`} />
                      Frame {index} · {formatTime(index / (job.media_metadata?.fps ?? 24))}
                    </a>)}</div></details>}
                </div>
              ))}
            </div>
          ) : (
            <p className="notice">
              No event evidence is available. {job.mode === "local_cv" ? "Inspect tracking diagnostics; uncertain observations cannot prove order." : "Mock uploads return UNKNOWN."}
            </p>
          )}
          <h3>Ordering constraints</h3>
          <ul className="checks">
            {result.constraints.map((check) => {
              const constraint = job.graph?.constraints.find(
                (item) => item.id === check.id,
              );
              return checkRow(
                check,
                constraint
                  ? constraintLabel(constraint)
                  : check.id,
              );
            })}
          </ul>
          {result.constraints.length === 0 && (
            <p className="subtle">No ordering constraints in this graph.</p>
          )}
          <details>
            <summary>{job.graph?.version === "2.0" ? "Event" : "Step"} observations ({result.steps.length})</summary>
            <ul className="checks">
              {result.steps.map((check) =>
                checkRow(
                  check,
                  (job.graph?.version === "2.0" ? job.graph.events : job.graph?.steps)
                    ?.find((step) => step.id === check.id)?.instruction ?? check.id,
                ),
              )}
            </ul>
          </details>
          {(result.conditions?.length ?? 0) > 0 && (
            <section aria-label="Condition results">
              <h3>Conditions and final states</h3>
              <ul className="checks">
                {result.conditions?.map((check) => {
                  const condition = job.graph?.version === "2.0"
                    ? job.graph.conditions.find((item) => item.id === check.id) : undefined;
                  return checkRow(check, condition
                    ? `${condition.instruction} (${condition.scope})` : check.id);
                })}
              </ul>
            </section>
          )}
          <p className="retention">
            Media expires {new Date(job.expires_at * 1000).toLocaleString()}.
            Run metadata is retained locally.
          </p>
        </>
      )}
      {["local_cv", "meta_sam"].includes(job.mode) && <section aria-label="Tracking diagnostics">
        <h3>Measured tracking quality</h3><p>Scores are conservative heuristics, not calibrated probabilities. Any lost or ambiguous identity invalidates that object's events.</p>
        {job.tracks?.map(track => <details key={track.object_id}><summary>{track.object_id}: {track.diagnostics.length ? track.diagnostics.join("; ") : "No tracking loss detected"}</summary>
          <pre>{JSON.stringify({ provenance: track.provenance, invalid_intervals: track.invalid_intervals, samples: track.samples }, null, 2)}</pre>
        </details>)}
        <details><summary>Raw event candidates and independent provenance</summary><pre>{JSON.stringify({ provenance: job.provenance, observations: job.observations }, null, 2)}</pre></details>
      </section>}
      {(job.inference_usage?.length ?? 0) > 0 && <section aria-label="Inference usage and cost"><h3>{job.execution_mode === "offline_capture_review" ? "Captured original inference usage and cost" : "Inference usage and cost"}</h3>
        {job.inference_usage?.map((usage, i) => <p key={i}>{usage.model}: reserved ${(usage.reserved_microusd / 1e6).toFixed(6)};
          {" "}{usage.usage_verified && usage.actual_microusd !== null ? `verified cost $${(usage.actual_microusd / 1e6).toFixed(6)}` : "actual usage uncertain; full reservation retained"}.</p>)}
      </section>}
    </section>
  );
}
