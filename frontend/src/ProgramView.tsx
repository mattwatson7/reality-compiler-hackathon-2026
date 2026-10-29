import { constraintLabel } from "./types";
import type { Observability, Predicate, SemanticEvent, SourceSpan, TaskGraph } from "./types";

function SourceQuote({ source }: { source: SourceSpan }) {
  return <p className="source-quote"><small>Source [{source.start}, {source.end}): “{source.quote}”</small></p>;
}

function ObservabilityNote({ item }: { item: Observability }) {
  return <div className={`observability ${item.observability.toLowerCase()}`}>
    <span className="mono">{item.observability}</span>
    {item.reason && <p>{item.reason}</p>}
  </div>;
}

function PredicateView({ predicate }: { predicate: Predicate | null }) {
  if (!predicate) return <p className="subtle">No supported visual predicate.</p>;
  return <div className="predicate">
    <code>{predicate.type}</code>
    <p>Object: <strong>{predicate.object_id}</strong></p>
    {"region_id" in predicate && <p>Region: <strong>{predicate.region_id}</strong></p>}
    {predicate.type === "visually_confirmed_state_change" && <>
      <p>{predicate.state_dimension}: {predicate.from_state} → {predicate.to_state}</p>
      <p>{predicate.visual_criteria}</p>
    </>}
  </div>;
}

function RequirementCard({ item }: { item: SemanticEvent }) {
  return <article className="graph-step">
    <span className="mono">{item.id}</span>
    <span className="requirement-kind">{item.required ? "Required" : "Optional"}</span>
    <h4>{item.instruction}</h4>
    <PredicateView predicate={item.predicate} />
    <ObservabilityNote item={item} />
    <SourceQuote source={item.source} />
  </article>;
}

export function ProgramView({ graph }: { graph: TaskGraph }) {
  const semantic = graph.version === "2.0";
  const requirements = semantic ? graph.events : graph.steps;
  return <div aria-label="Compiled program" className="semantic-program">
    <div className="program-meta mono">
      <span>TaskGraph v{graph.version}</span>
      <span>Compilation source: {semantic ? graph.compilation_source : "legacy"}</span>
    </div>
    <section aria-label="Program objects">
      <h3>Objects</h3>
      {graph.objects.length === 0 && <p className="subtle">No objects declared.</p>}
      <div className="graph-steps">
        {graph.objects.map((object) => <article className="graph-step" key={object.id}>
          <span className="mono">{object.id}</span>
          <h4>{object.label}</h4>
          {"description" in object && <p>{object.description}</p>}
          {"grounding_prompt" in object && object.grounding_prompt && <p>{object.grounding_prompt}</p>}
        </article>)}
      </div>
    </section>
    {semantic && <section aria-label="Program regions">
      <h3>Visible image regions</h3>
      <p className="field-help">Region transitions refer to visible image areas; they do not establish physical containment.</p>
      {graph.regions.length === 0 && <p className="subtle">No regions declared.</p>}
      <div className="graph-steps">
        {graph.regions.map((region) => <article className="graph-step" key={region.id}>
          <span className="mono">{region.id}</span>
          <h4>{region.description}</h4>
          <p>{region.grounding_prompt}</p>
          <p className="mono">{region.coordinate_semantics}</p>
          <ObservabilityNote item={region} />
        </article>)}
      </div>
    </section>}
    <section aria-label="Program events">
      <h3>{semantic ? "Events" : "Legacy steps"}</h3>
      <div className="graph-steps">
        {semantic ? graph.events.map((event) => <RequirementCard key={event.id} item={event} />)
          : graph.steps.map((step) => <article key={step.id} className="graph-step">
            <span className="mono">{step.id}</span><p>{step.instruction}</p>
            {step.object_ids.length > 0 && <p>Objects: {step.object_ids.join(", ")}</p>}
          </article>)}
      </div>
      {requirements.length === 0 && <p className="subtle">No events declared.</p>}
    </section>
    <section aria-label="Program temporal constraints">
      <h3>Temporal constraints</h3>
      {graph.constraints.length === 0 ? <p className="subtle">No temporal constraints. Events are unordered.</p>
        : <ul className="temporal-edges">{graph.constraints.map((constraint) => <li key={constraint.id}>
          <span className="mono">{constraint.id}</span> <strong>{constraintLabel(constraint)}</strong>
          {"source" in constraint && <SourceQuote source={constraint.source} />}
        </li>)}</ul>}
    </section>
    {semantic && (["during", "final"] as const).map((scope) => <section key={scope} aria-label={scope === "final" ? "Program final states" : "Program conditions"}>
      <h3>{scope === "final" ? "Final states" : "Conditions during the clip"}</h3>
      {scope === "final" && <p className="field-help">Final states require evidence at the observable end of the clip.</p>}
      <div className="graph-steps">
        {graph.conditions.filter((condition) => condition.scope === scope).map((condition) => <RequirementCard key={condition.id} item={condition} />)}
      </div>
      {!graph.conditions.some((condition) => condition.scope === scope) && <p className="subtle">None declared.</p>}
    </section>)}
    <details>
      <summary>Inspect TaskGraph JSON · {requirements.length} {semantic ? "events" : "steps"} / {graph.constraints.length} constraints</summary>
      <pre>{JSON.stringify(graph, null, 2)}</pre>
    </details>
  </div>;
}
