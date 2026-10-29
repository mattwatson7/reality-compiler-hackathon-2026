"""Server-only fixed-origin Meta transport. No network occurs at import or in CI.

Live generation requires explicit server gates, discovered entitlement and a
verified integer reservation. Errors deliberately exclude remote payloads/keys.
"""

import base64
import http.client
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import SecretStr

from backend.app.config import ROOT
from backend.app.store import Store

MAX_RESPONSE = 32 * 1024 * 1024
MAX_REQUEST = 96 * 1024 * 1024
MODEL_IDS = ("sam-3.1", "muse-wonder-1.0", "muse-spark-1.3")


class MetaDisabled(RuntimeError):
    pass


class MetaContractError(RuntimeError):
    pass


def load_key(root: Path = ROOT) -> SecretStr:
    value = os.getenv("MODEL_API_KEY")
    if not value:
        path = root / ".env"
        if path.is_file() and path.stat().st_size <= 65536:
            value = dotenv_values(path, interpolate=False).get("MODEL_API_KEY")
    return SecretStr((value or "").strip())


@dataclass(frozen=True)
class ModelCatalog:
    ids: tuple[str, ...] = ()
    authenticated: bool = False

    def supports(self, model: str) -> bool:
        return self.authenticated and model in self.ids


def parse_sse(content: bytes) -> dict[str, Any]:
    """Require a terminal completed response; truncated streams never yield tracks."""
    if len(content) > MAX_RESPONSE:
        raise MetaContractError("Meta response exceeded size bound")
    deltas: list[str] = []
    completed: dict[str, Any] | None = None
    try:
        for block in content.decode("utf-8").replace("\r\n", "\n").split("\n\n"):
            lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
            if not lines:
                continue
            data = "\n".join(lines)
            if data == "[DONE]":
                continue
            event = json.loads(data)
            kind = event.get("type")
            if completed is not None:
                raise ValueError("Unexpected event after completion")
            if kind == "response.output_text.delta":
                if not isinstance(event.get("delta"), str):
                    raise ValueError("Invalid delta")
                deltas.append(event["delta"])
            elif kind == "response.completed":
                completed = event["response"]
                if not isinstance(completed, dict):
                    raise ValueError("Invalid completed response")
            elif kind in {"error", "response.failed", "response.incomplete"}:
                raise ValueError("Failed stream")
        if completed is None:
            raise ValueError("No completion")
        combined = "".join(deltas)
        if "output_text" in completed and completed["output_text"] != combined:
            raise ValueError("Conflicting terminal text")
        return {**completed, "output_text": combined}
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise MetaContractError("Malformed or partial Meta stream; no evidence accepted") from None


class MetaClient:
    def __init__(
        self,
        *,
        key: SecretStr,
        store: Store | None = None,
        paid_enabled: bool = False,
        smoke_approved: bool = False,
        catalog: ModelCatalog | None = None,
        request: Callable[[str, str, dict[str, Any] | None], dict[str, Any]] | None = None,
    ) -> None:
        self._key = key
        self.store = store
        self.paid_enabled, self.smoke_approved = paid_enabled, smoke_approved
        self.catalog = catalog or ModelCatalog()
        self._request = request or self._http
        self._synthetic = request is not None
        self._slot = threading.BoundedSemaphore(1)
        self.usage: list[dict[str, Any]] = []
        self._pending: dict[int, tuple[dict[str, Any], str, int | None, dict[str, Any]]] = {}

    def discover(self) -> ModelCatalog:
        if not self._key.get_secret_value():
            raise MetaDisabled("MODEL_API_KEY is not configured in the backend")
        raw = self._request("GET", "/v1/models", None)
        try:
            if raw["object"] != "list" or not isinstance(raw["data"], list):
                raise ValueError("Invalid catalog")
            ids = tuple(item["id"] for item in raw["data"])
            if any(
                item.get("object") != "model"
                or type(item.get("created")) is not int
                or item["created"] < 0
                or not isinstance(item.get("owned_by"), str)
                for item in raw["data"]
            ):
                raise ValueError("Invalid model metadata")
            if len(ids) > 1000 or any(not isinstance(x, str) or len(x) > 200 for x in ids):
                raise ValueError("Invalid model IDs")
        except (ValueError, KeyError, TypeError):
            raise MetaContractError("Invalid model discovery response") from None
        self.catalog = ModelCatalog(ids, True)
        return self.catalog

    def dispatch(
        self, path: str, body: dict[str, Any], *, model: str, upper_bound_microusd: int
    ) -> dict[str, Any]:
        if not (
            self.paid_enabled
            and self.smoke_approved
            and self.catalog.supports(model)
            and self.store is not None
            and self._key.get_secret_value()
        ):
            raise MetaDisabled(
                "Paid inference disabled: approval, credentials and entitlement required"
            )
        if (
            path not in {"/v1/responses", "/v1/chat/completions"}
            or model not in MODEL_IDS
            or type(upper_bound_microusd) is not int
            or upper_bound_microusd <= 0
        ):
            raise MetaDisabled("A verified positive request-cost bound is required")
        if body.get("model", model) != model or body.get("stream") is True:
            raise MetaDisabled("Only bounded nonstreaming dispatch is enabled")
        if any(body.get(field) for field in ("tools", "tool_choice", "web_search")):
            raise MetaDisabled("Tools and additional billed capabilities are disabled")
        if model == "sam-3.1":
            if path != "/v1/responses":
                raise MetaDisabled("SAM requires the Responses endpoint")
            verified_bound = self._validate_video_request(body)
        else:
            output_limit = body.get("max_completion_tokens")
            if (
                path != "/v1/chat/completions"
                or type(output_limit) is not int
                or not 1 <= output_limit <= 4096
            ):
                raise MetaDisabled("Text generation requires an explicit bounded output limit")
            verified_bound = (
                4 * 1_048_576 + 20 * output_limit
                if model == "muse-wonder-1.0"
                else (125 * 1_048_576 + 425 * output_limit + 99) // 100
            )
        upper_bound_microusd = max(upper_bound_microusd, verified_bound)
        if not self._slot.acquire(blocking=False):
            raise MetaDisabled("Meta request concurrency limit reached")
        try:
            reservation = self.store.reserve_cost(model, upper_bound_microusd)
            audit = {
                "model": model,
                "reserved_microusd": upper_bound_microusd,
                "actual_microusd": None,
                "usage_verified": False,
            }
            self.usage.append(audit)
            try:
                response = self._request("POST", path, body)
            except Exception:
                raise MetaContractError("Meta request failed; full reservation retained") from None
            actual = self._actual_cost(model, response, upper_bound_microusd)
            usage = response.get("usage", {})
            if model == "sam-3.1" and body:
                if (
                    not isinstance(usage, dict)
                    or type(usage.get("video_frames_processed")) is not int
                    or usage.get("video_frames_processed") != verified_bound // 200
                ):
                    actual = None
            if model != "sam-3.1" and isinstance(usage, dict):
                if (
                    type(usage.get("prompt_tokens")) is not int
                    or type(usage.get("completion_tokens")) is not int
                    or usage.get("prompt_tokens", 0) > 1_048_576
                    or usage.get("completion_tokens", 0) > body["max_completion_tokens"]
                ):
                    actual = None
            self._pending[id(response)] = (response, reservation, actual, audit)
            return response
        finally:
            self._slot.release()

    def acknowledge(self, response: dict[str, Any]) -> None:
        """Only validated adapter success may settle verified actual usage."""
        pending = self._pending.pop(id(response), None)
        if pending is None or pending[0] is not response:
            return
        _, reservation, actual, audit = pending
        if actual is not None and self.store is not None:
            self.store.settle_cost(reservation, actual)
            audit.update(actual_microusd=actual, usage_verified=True)

    def fork(self) -> "MetaClient":
        client = MetaClient(
            key=self._key,
            store=self.store,
            paid_enabled=self.paid_enabled,
            smoke_approved=self.smoke_approved,
            catalog=self.catalog,
            request=self._request if self._synthetic else None,
        )
        client._slot = self._slot
        return client

    def _validate_video_request(self, body: dict[str, Any]) -> int:
        if self._synthetic and not body:
            # Legacy synthetic transport-only tests have no media and use the
            # conservative maximum. This path cannot open a real connection.
            return 720 * 200
        from backend.app.perception import inspect_video

        try:
            messages = body["input"]
            if len(messages) != 1 or messages[0]["role"] != "user":
                raise ValueError("Messages")
            parts = messages[0]["content"]
            videos = [p for p in parts if p["type"] == "input_video"]
            texts = [p for p in parts if p["type"] == "input_text"]
            if len(parts) != 2 or len(videos) != 1 or len(texts) != 1:
                raise ValueError("Parts")
            if (
                body.get("metadata", {}).get("propagation_direction") != "forward"
                or not texts[0]["text"].startswith("<0f>")
                or texts[0]["text"].count("f>") != 1
            ):
                raise ValueError("Tracking range")
            url = videos[0]["video_url"]
            prefix = "data:video/mp4;base64,"
            if not isinstance(url, str) or not url.startswith(prefix) or len(url) > MAX_REQUEST:
                raise ValueError("Media")
            decoded = base64.b64decode(url[len(prefix) :], validate=True)
            assert self.store is not None
            with tempfile.TemporaryDirectory(dir=self.store.path.parent) as directory:
                path = Path(directory) / "bounded.mp4"
                path.write_bytes(decoded)
                metadata = inspect_video(path)
            prompt = texts[0]["text"]
            pattern = (
                r"([1-9][0-9]*)<\|box;x1=([0-9]+);y1=([0-9]+);x2=([0-9]+);y2=([0-9]+);"
                r"w=([0-9]+);h=([0-9]+)\|>"
            )
            records = prompt[4:].split(",")
            ids = set()
            if not 1 <= len(records) <= 16:
                raise ValueError("Object count")
            for record in records:
                match = re.fullmatch(pattern, record)
                if match is None:
                    raise ValueError("Prompt grammar")
                identifier, x1, y1, x2, y2, width, height = map(int, match.groups())
                if (
                    identifier in ids
                    or width != metadata["width"]
                    or height != metadata["height"]
                    or not 0 <= x1 <= x2 < width
                    or not 0 <= y1 <= y2 < height
                ):
                    raise ValueError("Prompt geometry")
                ids.add(identifier)
            return max(50, metadata["frame_count"]) * 200
        except Exception:
            raise MetaDisabled("SAM media/range lacks a verified frame-count cost bound") from None

    @staticmethod
    def _actual_cost(model: str, response: dict[str, Any], bound: int) -> int | None:
        usage = response.get("usage")
        if response.get("model") != model or not isinstance(usage, dict):
            return None
        if model == "sam-3.1":
            frames = usage.get("video_frames_processed")
            if type(frames) is not int or not 50 <= frames <= 720:
                return None
            cost = frames * 200
        else:
            prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if (
                type(prompt) is not int
                or type(completion) is not int
                or min(prompt, completion) < 0
                or usage.get("total_tokens") != prompt + completion
            ):
                return None
            details = usage.get("prompt_tokens_details")
            cached = details.get("cached_tokens") if isinstance(details, dict) else None
            if type(cached) is not int or not 0 <= cached <= prompt:
                return None
            if model == "muse-wonder-1.0":
                cost = (prompt - cached) * 4 + (cached + 4) // 5 + completion * 20
            else:
                cost = ((prompt - cached) * 125 + cached * 15 + completion * 425 + 99) // 100
        return cost if 0 <= cost <= bound else None

    def _http(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
            raise MetaDisabled("Meta network requests are disabled in CI and automated tests")
        if (method, path) not in {
            ("GET", "/v1/models"),
            ("POST", "/v1/responses"),
            ("POST", "/v1/chat/completions"),
        }:
            raise MetaDisabled("Unsupported Meta endpoint")
        encoded = json.dumps(body).encode() if body is not None else None
        if encoded is not None and len(encoded) > MAX_REQUEST:
            raise MetaContractError("Meta request exceeds byte limit")
        connection = http.client.HTTPSConnection("api.meta.ai", timeout=30)
        started = time.monotonic()
        try:
            connection.request(
                method,
                path,
                body=encoded,
                headers={
                    "Authorization": "Bearer " + self._key.get_secret_value(),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise MetaContractError(f"Meta HTTP {response.status}; remote details suppressed")
            chunks = bytearray()
            while True:
                part = response.read1(65536)
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > MAX_RESPONSE or time.monotonic() - started > 120:
                    raise MetaContractError("Meta response exceeded byte/time limits")
            if "text/event-stream" in response.getheader("Content-Type", ""):
                raise MetaContractError("Unexpected stream for nonstreaming request")
            parsed = json.loads(chunks)
            if not isinstance(parsed, dict):
                raise ValueError("Not an object")
            return parsed
        except MetaContractError:
            raise
        except Exception:
            raise MetaContractError(
                "Meta connection or response failed; details suppressed"
            ) from None
        finally:
            connection.close()
