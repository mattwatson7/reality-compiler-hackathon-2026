import { useEffect, useState } from "react";
import { HttpError, request } from "./api";
import { EvidenceViewer } from "./EvidenceViewer";
import { ProgramView } from "./ProgramView";
import { FirstFrameSelection } from "./FirstFrameSelection";
import { ReEvaluationPanel } from "./ReEvaluationPanel";
import type { Fixture, Health, Job, Ledger, TaskGraph } from "./types";

const DEFAULT_PROCEDURE =
  "Move the blue block into the visible marked region before moving the cup into that region.";

export function App() {
  const [procedure, setProcedure] = useState(DEFAULT_PROCEDURE);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [jobId, setJobId] = useState<string | null>(() => new URLSearchParams(window.location.search).get("run"));
  const [preview, setPreview] = useState<TaskGraph | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [perceptionMode, setPerceptionMode] = useState("local_cv");
  const [footageOrigin, setFootageOrigin] = useState("unknown");
  const busy =
    submitting ||
    (jobId !== null && (!job || ["queued", "processing"].includes(job.status)));

  useEffect(() => {
    const url = new URL(window.location.href);
    if (jobId) url.searchParams.set("run", jobId);
    else url.searchParams.delete("run");
    window.history.replaceState(null, "", url);
  }, [jobId]);

  useEffect(() => {
    const controller = new AbortController();
    request<Fixture[]>("/api/fixtures", { signal: controller.signal })
      .then(setFixtures)
      .catch((err) => {
        if (!controller.signal.aborted) setError(String(err));
      });
    request<Health>("/api/health", { signal: controller.signal })
      .then(setHealth)
      .catch(() => {});
    request<Ledger>("/api/costs", { signal: controller.signal })
      .then(setLedger)
      .catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    let loaded = false;
    async function poll() {
      try {
        const latest = await request<Job>(`/api/jobs/${jobId}`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        failures = 0;
        if (!loaded) {
          setProcedure(latest.procedure);
          setPerceptionMode(latest.mode);
          loaded = true;
        }
        setJob(latest);
        if (latest.status === "completed") {
          request<Ledger>("/api/costs", { signal: controller.signal })
            .then(setLedger)
            .catch(() => {});
        }
        if (!["expired", "failed"].includes(latest.status)) {
          timer = setTimeout(poll, latest.status === "completed" ? 15000 : 500);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(`Status check failed: ${String(err)}`);
          failures += 1;
          if (
            (err instanceof HttpError &&
              [400, 404, 410].includes(err.status)) ||
            failures >= 3
          ) {
            setJobId(null);
          } else timer = setTimeout(poll, 3000);
        }
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [jobId]);

  async function runDemo(fixture: Fixture) {
    setSubmitting(true);
    setError(null);
    setJob(null);
    setJobId(null);
    setPreview(null);
    setProcedure(fixture.procedure);
    try {
      const response = await request<{ id: string }>(
        `/api/jobs/demo/${fixture.id}`,
        { method: "POST" },
      );
      setJobId(response.id);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function compile() {
    setSubmitting(true);
    setError(null);
    setJob(null);
    setJobId(null);
    try {
      setPreview(
        await request<TaskGraph>("/api/compile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ procedure }),
        }),
      );
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function upload() {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    setJob(null);
    setJobId(null);
    setPreview(null);
    setUploadProgress(0);
    const form = new FormData();
    form.append("procedure", procedure);
    form.append("video", file);
    form.append("perception_mode", perceptionMode);
    form.append("footage_origin", footageOrigin);
    try {
      const response = await request<{ id: string }>("/api/jobs/upload", {
        method: "POST",
        body: form,
      });
      setUploadProgress(100);
      setJobId(response.id);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
      setUploadProgress(null);
    }
  }

  const graph = preview ?? job?.graph;

  return (
    <main className={job?.execution_mode === "offline_capture_review" ? "capture-review" : undefined}>
      <header className="masthead">
        <a href="/" className="brand">
          <span className="brand-symbol">⌘</span>
          <span>
            REALITY<span className="brand-light">COMPILER</span>
          </span>
        </a>
        <div className="header-meta">
          <span className="status-dot" />
          VERIFICATION STUDIO <span className="version">M05</span>
        </div>
      </header>
      {job?.execution_mode !== "offline_capture_review" && <div className="mode-banner">
        <span className="mode-tag">{health?.meta?.sam_selectable ? "META SAM / LOCAL CV" : "LOCAL CV / FIXTURE DEMOS"}</span>
        <span>
          {health?.meta?.paid_inference_enabled ? "Meta inference is enabled by server configuration. " : "No live model inference. "}
          Local OpenCV processes selected objects in actual frames.
          Demo events are declared synthetic data. Meta inference requires explicit paid authorization.
        </span>
      </div>}
      {job?.execution_mode === "offline_capture_review" && <section className="capture-context" aria-label="Captured Meta evidence">
        <p role="status"><strong>Generated footage · Offline review of captured Meta evidence · No new inference</strong></p>
        <div className="model-roles">
          <span><strong>Muse Wonder</strong>Original requirements · independently validated</span>
          <span><strong>SAM 3.1</strong>Captured masks and object tracks</span>
          <span><strong>Deterministic evaluator</strong>PASS / FAIL / UNKNOWN · revisions compile locally</span>
        </div>
        <p className="field-help">Muse Spark supports bounded final-state interpretation in separate captured runs. It was not used for this order comparison. Paid inference is disabled for this review.</p>
      </section>}
      {health?.meta && job?.execution_mode !== "offline_capture_review" && <p className="notice" aria-label="Meta integration status">
        Meta catalog: {health.meta.catalog_authenticated ? health.meta.models.join(", ") : "not discovered"}.
        {" "}Paid inference: {health.meta.paid_inference_enabled ? "enabled by server configuration" : "disabled"}.
        {" "}{health.meta.reason}
      </p>}
      {job?.execution_mode !== "offline_capture_review" && <div className="capability-status" aria-label="Provider capabilities">
        <span>Real Muse compilation: {health?.real_muse_compilation === true ? "active" : health?.real_muse_compilation === false ? "inactive" : "unavailable"}</span>
        <span>Real video verification: {health?.real_video_verification === true ? "active" : health?.real_video_verification === false ? "inactive" : "unavailable"}</span>
      </div>}
      <section className="intro">
        <span className="eyebrow">LANGUAGE → PROGRAM → EVIDENCE</span>
        <h1>
          Make procedures
          <br />
          <em>verifiable.</em>
        </h1>
        <p>
          Turn physical instructions into an inspectable verification program.
          <br />
          Describe what should happen. Show what happened. Prove whether they match.
        </p>
        <div className="intro-index mono">
          REALITY COMPILER
          <br />
          HACKATHON BUILD / 2026
        </div>
      </section>
      {error && (
        <div role="alert" className="error">
          <strong>Action needs attention.</strong> {error}
        </div>
      )}
      <div className="workspace">
        <section className="editor panel" aria-label="Procedure editor">
          <div className="section-heading">
            <div>
              <span className="eyebrow">01 / DEFINE</span>
              <h2>The procedure</h2>
            </div>
            <span className="mono subtle">TASKGRAPH v2.0</span>
          </div>
          <label htmlFor="procedure">Physical instructions</label>
          <textarea
            id="procedure"
            aria-label="Procedure"
            maxLength={10000}
            rows={7}
            value={procedure}
            disabled={busy}
            onChange={(event) => {
              setProcedure(event.target.value);
              setPreview(null);
            }}
          />
          <p className="field-help">
            Upload compiler: {" "}
            {health?.real_muse_compilation && perceptionMode === "meta_sam"
              ? "Muse Wonder interprets your instructions with independent source and semantic validation. "
              : "The local rules compiler supports a limited vocabulary of visible actions and explicit ordering. "}
            Unsupported requirements remain explicit and prevent PASS.
            Upload to compile once, then select each object and region on frame zero.
          </p>
          <button
            className="secondary full"
            disabled={busy || !procedure.trim()}
            onClick={() => void compile()}
          >
            Compile TaskGraph{health?.real_muse_compilation ? " · paid Wonder" : ""} <span>↗</span>
          </button>
          <div className="divider" />
          <h3>Try a known sequence</h3>
          <p className="field-help">
            Two synthetic videos. Same instructions. Different order.
          </p>
          <div className="demo-buttons">
            {fixtures.map((fixture) => (
              <button
                key={fixture.id}
                disabled={busy}
                className="demo-button"
                onClick={() => void runDemo(fixture)}
              >
                <span className={`demo-marker ${fixture.id}`} />
                {fixture.title}
                <span>↗</span>
              </button>
            ))}
          </div>
          <div className="divider" />
          <label className="upload-zone" htmlFor="video-file">
            <span className="upload-icon">↑</span>
            <strong>{file ? file.name : "Bring your own recording"}</strong>
            <span>MP4, MOV or WebM · up to 100 MB / 30 sec · SAM or local CV</span>
            <input
              id="video-file"
              aria-label="Upload video"
              type="file"
              accept="video/*"
              disabled={busy}
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setError(null);
                setJob(null);
                setJobId(null);
              }}
            />
          </label>
          <label>Upload perception <select aria-label="Upload perception" disabled={busy} value={perceptionMode} onChange={e => setPerceptionMode(e.target.value)}>
            <option value="local_cv">Local OpenCV · real pixels, no Meta model</option>
            <option value="meta_sam" disabled={!health?.meta?.sam_selectable}>Meta SAM · {health?.meta?.sam_selectable ? "configured / paid" : "paid authorization required"}</option>
            <option value="mock-upload">Mock upload · UNKNOWN</option>
            <option value="fixture">Fixture Demo · synthetic · use sequence buttons above</option>
          </select></label>
          <label>Recording source <select aria-label="Recording source" disabled={busy} value={footageOrigin} onChange={e => setFootageOrigin(e.target.value)}>
            <option value="unknown">Unspecified source</option>
            <option value="genuine_camera">Genuine camera recording · user declared</option>
            <option value="generated">Generated demonstration · user declared</option>
          </select></label>
          <button
            className="primary full"
            disabled={busy || !file || !procedure.trim() || perceptionMode === 'fixture'}
            onClick={() => void upload()}
          >
            {uploadProgress !== null
              ? "Uploading video…"
              : "Verify uploaded video"}
            <span>→</span>
          </button>
          <p className="field-help">
            Local CV requires a static camera, two distinctly colored saturated objects and a plain table.
            Occlusion or ambiguous tracking yields UNKNOWN. Region entry describes image geometry.
          </p>
        </section>
        <div className="right-column panel">
          {(busy || job) && (
            <div className="job-progress" role="status" aria-live="polite">
              <span className="eyebrow">
                {job?.status.toUpperCase() ?? "SUBMITTING"}
              </span>
              <span>{job?.message ?? "Sending request…"}</span>
              <span className="mono">{job?.progress ?? 0}%</span>
              <progress
                aria-label="Job progress"
                value={job?.progress ?? 0}
                max={100}
              />
              {job?.error && <p role="alert">{job.error}</p>}
            </div>
          )}
          {job?.status === "awaiting_initialization" ? (
            <FirstFrameSelection key={job.id} job={job} onSubmitted={() => setJob({ ...job, status: "queued", message: "Tracking queued" })} />
          ) : job ? (
            <EvidenceViewer key={job.id} job={job} />
          ) : (
            <section className="review">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">02 / OBSERVE</span>
                  <h2>Evidence monitor</h2>
                </div>
                <span className="mono subtle">AWAITING INPUT</span>
              </div>
              <div className="empty-monitor initial">
                <div className="crosshair">＋</div>
                <h3>Every verdict starts with evidence.</h3>
                <p>
                  Run a demo sequence or upload a recording.
                  <br />
                  Your video and timestamped results will appear here.
                </p>
                <div className="empty-labels">
                  <span>PASS</span>
                  <span>FAIL</span>
                  <span>UNKNOWN</span>
                </div>
              </div>
              <div className="monitor-footer mono">
                <span>DETERMINISTIC ORDERING</span>
                <span>INSPECTABLE EVIDENCE</span>
              </div>
            </section>
          )}
        </div>
      </div>
      {job?.result && <ReEvaluationPanel key={job.id} job={job} paidCompiler={health?.real_muse_compilation === true} />}
      <section className="program panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">03 / INSPECT</span>
            <h2>The verification program</h2>
          </div>
          <span className="mono subtle">STRICT JSON SCHEMA</span>
        </div>
        {graph ? (
          <ProgramView graph={graph} />
        ) : (
          <p className="subtle">
            Compile instructions to inspect objects, events, conditions and
            explicit temporal constraints.
          </p>
        )}
      </section>
      <footer>
        <span>
          REALITY COMPILER <span className="subtle">/ MILESTONE 05</span>
        </span>
        <span className="mono">
          {job?.execution_mode === "offline_capture_review" ? "ISOLATED REVIEW LEDGER" : "API BUDGET"}{" "}
          {ledger
            ? `$${(ledger.committed_microusd / 1000000).toFixed(2)} / $${(ledger.cap_microusd / 1000000).toFixed(2)}`
            : "UNAVAILABLE"}{" "}
          · {job?.mode === 'meta_sam' ? 'META SAM' : 'LOCAL CV / NO SAM'}
        </span>
      </footer>
    </main>
  );
}
