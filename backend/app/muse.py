"""Disabled Muse contract boundary with an exclusively offline fixture transport.

Public contracts and Standard prices: docs/meta-api-contracts.md (2026-10-27).
No HTTP client, credentials, or live dispatch is implemented here. Bounds in offline
fixtures are test assertions; they do not establish a verified live token bound.
Source matching establishes textual traceability, not semantic faithfulness.
"""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.schemas import TaskGraph
from backend.app.store import Store

ENDPOINT = "https://api.meta.ai/v1/chat/completions"
MODEL = "muse-wonder-1.0"
MAX_RESPONSE_BYTES = 1_000_000


class MuseDisabled(RuntimeError):
    """Live access and a conservative live request bound remain unverified."""


class MuseContractError(RuntimeError):
    """Safe diagnostics deliberately exclude provider payloads and credentials."""


@dataclass(frozen=True)
class DispatchBound:
    max_input_tokens: int
    max_completion_tokens: int
    verified: bool = False

    def valid(self) -> bool:
        return (
            self.verified is True
            and type(self.max_input_tokens) is int
            and type(self.max_completion_tokens) is int
            and 0 < self.max_input_tokens <= 1_048_576
            and 0 < self.max_completion_tokens <= 1_048_576
            and self.max_input_tokens + self.max_completion_tokens <= 1_048_576
        )

    @property
    def microusd(self) -> int:
        # Conservative documented Standard rates, with no cache discount.
        return 4 * self.max_input_tokens + 20 * self.max_completion_tokens


@dataclass(frozen=True)
class OfflineResponse:
    status_code: int
    content: bytes


class OfflineTransport:
    """Consumes synthetic HTTP responses; cannot open a connection or run callbacks."""

    def __init__(self, responses: list[OfflineResponse | Exception]) -> None:
        self._responses = iter(responses)
        self.requests: list[dict[str, Any]] = []

    def dispatch(self, request: dict[str, Any]) -> OfflineResponse:
        self.requests.append(request)
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


class _EnvelopeModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")


class _Message(_EnvelopeModel):
    role: Literal["assistant"]
    content: str | None
    refusal: str | None = None
    tool_calls: list[Any] | None = None
    function_call: dict[str, Any] | None = None


class _Choice(_EnvelopeModel):
    index: Literal[0]
    finish_reason: str
    message: _Message


class _Envelope(_EnvelopeModel):
    id: str = Field(min_length=1)
    object: Literal["chat.completion"]
    created: int = Field(ge=0)
    model: Literal["muse-wonder-1.0"]
    choices: list[_Choice] = Field(min_length=1, max_length=1)
    usage: Any = None


class _Cached(_EnvelopeModel):
    cached_tokens: int = Field(ge=0)


class _Reasoning(_EnvelopeModel):
    reasoning_tokens: int = Field(ge=0)


class _Usage(_EnvelopeModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    prompt_tokens_details: _Cached | None = None
    completion_tokens_details: _Reasoning | None = None


def strict_graph_schema() -> dict[str, Any]:
    """Convert Pydantic unions to the documented strict structured-output subset.

    Defaults are omitted from the wire schema: every property is explicitly sent,
    including null for application fields whose type allows null.
    """
    schema = TaskGraph.model_json_schema()

    def convert(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            value.pop("discriminator", None)
            if "oneOf" in value:
                value["anyOf"] = value.pop("oneOf")
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for child in value.values():
                convert(child)
        elif isinstance(value, list):
            for child in value:
                convert(child)

    convert(schema)
    return schema


class MuseWonderCompiler:
    """CompilerProvider implementation available exclusively for offline contracts.

    Constructing without a concrete OfflineTransport fails closed. Enabling live
    operation needs a separately reviewed transport, account gate, verified pricing
    and input bound including schema/prompt overhead, timeout and response limits.
    """

    def __init__(
        self,
        *,
        store: Store | None = None,
        transport: OfflineTransport | None = None,
        bound: DispatchBound | None = None,
    ) -> None:
        if (
            store is None
            or type(transport) is not OfflineTransport
            or bound is None
            or not bound.valid()
        ):
            raise MuseDisabled(
                "Live Muse compilation is disabled; only offline fixtures are enabled"
            )
        self.store = store
        self.transport = transport
        self.bound = bound

    def compile(self, procedure: str) -> TaskGraph:
        if not isinstance(procedure, str) or not procedure.strip() or len(procedure) > 10000:
            raise ValueError("Enter a procedure between 1 and 10000 characters")
        for attempt in range(2):
            request = self._request(procedure, repair=attempt == 1)
            reservation = self.store.reserve_cost("muse-offline-contract", self.bound.microusd)
            try:
                response = self.transport.dispatch(request)
            except Exception:
                raise MuseContractError("Compiler transport failed; reservation retained") from None
            envelope = self._envelope(response)
            content = envelope.choices[0].message.content
            try:
                if content is None:
                    raise ValueError("Missing graph")
                graph = TaskGraph.model_validate_json(content)
                if graph.procedure != procedure or graph.compilation_source != "muse":
                    raise ValueError("Graph does not preserve source")
            except (ValidationError, ValueError):
                if attempt == 0:
                    continue
                raise MuseContractError(
                    "Compiler graph failed validation after one repair"
                ) from None
            actual = self._verified_cost(envelope.usage)
            if actual is not None:
                self.store.settle_cost(reservation, actual)
            return graph
        raise MuseContractError("Compiler graph failed validation")

    def _request(self, procedure: str, *, repair: bool) -> dict[str, Any]:
        instruction = (
            "Compile the exact procedure into TaskGraph v2 with compilation_source muse. "
            "Preserve verbatim procedure and exact character source spans. Only explicit temporal "
            "relations create edges. Unsupported or ambiguous requirements must remain explicit. "
            "Do not invent objects, references, visible semantics or ordering. Emit all fields, "
            "using null where allowed. object_visible establishes visible identity only. "
            "object_entered_region requires a visible outside-to-inside transition; "
            "object_exited_region requires a visible inside-to-outside transition. "
            "Occlusion does not establish a transition, insertion or physical containment. "
            "visually_confirmed_state_change requires distinct visible before/after states "
            "and explicit visual criteria. Hidden properties such as sterility, torque, charge "
            "or a hidden seal are UNSUPPORTED with a reason, never invented visible predicates. "
            "Preserve optional wording; do not invent optionality or make optional events "
            "mandatory through constraints. Preserve unordered actions without edges. "
            "Final conditions must describe supported observable end states, "
            "not transient intermediate events."
        )
        if repair:
            instruction += " The previous graph was invalid. Produce a corrected graph."
        return {
            "method": "POST",
            "url": ENDPOINT,
            "body": {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": procedure},
                ],
                "max_completion_tokens": self.bound.max_completion_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "task_graph_v2",
                        "strict": True,
                        "schema": strict_graph_schema(),
                    },
                },
            },
        }

    @staticmethod
    def _envelope(response: OfflineResponse) -> _Envelope:
        if response.status_code != 200:
            raise MuseContractError("Compiler HTTP response rejected; reservation retained")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise MuseContractError("Compiler response exceeded size limit; reservation retained")
        try:
            envelope = _Envelope.model_validate_json(response.content)
        except (ValidationError, ValueError):
            raise MuseContractError("Malformed compiler response; reservation retained") from None
        choice = envelope.choices[0]
        if (
            choice.finish_reason != "stop"
            or choice.message.refusal is not None
            or choice.message.tool_calls
            or choice.message.function_call is not None
        ):
            raise MuseContractError("Compiler refused or did not complete; reservation retained")
        return envelope

    def _verified_cost(self, raw: Any) -> int | None:
        try:
            usage = _Usage.model_validate(raw)
        except ValidationError:
            return None
        if usage.prompt_tokens_details is None:
            # The documented optional field does not establish zero cache use when absent.
            return None
        if (
            usage.prompt_tokens + usage.completion_tokens != usage.total_tokens
            or usage.prompt_tokens > self.bound.max_input_tokens
            or usage.completion_tokens > self.bound.max_completion_tokens
            or (
                usage.prompt_tokens_details is not None
                and usage.prompt_tokens_details.cached_tokens > usage.prompt_tokens
            )
            or (
                usage.completion_tokens_details is not None
                and usage.completion_tokens_details.reasoning_tokens > usage.completion_tokens
            )
        ):
            return None
        cached = usage.prompt_tokens_details.cached_tokens
        # Standard rates in micro-USD: 4 uncached, 1/5 cached, 20 output.
        # Round the complete verified charge up to the integer ledger unit, never use floats.
        actual = 4 * (usage.prompt_tokens - cached) + (cached + 4) // 5
        actual += 20 * usage.completion_tokens
        return actual if actual <= self.bound.microusd else None
