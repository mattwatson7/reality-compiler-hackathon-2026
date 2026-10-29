"""Check the built container's frontend, fixture evaluator and disabled paid gates.

Only loopback HTTP is accepted. No credentials, live models, or genuine recordings.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def validate_health(health: dict[str, Any]) -> None:
    meta = health.get("meta", {})
    if meta.get("paid_inference_enabled") is not False or meta.get("sam_selectable") is not False:
        raise ValueError("Container smoke requires paid inference disabled before any POST")
    if health.get("mode") != "fixture" or health.get("real_muse_compilation") is not False:
        raise ValueError("Container smoke requires the offline fixture compiler")


def wait_for_health(request: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    while True:
        try:
            return request()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            # Docker's mapped port can accept then reset while the application
            # imports. Retry only this read-only readiness probe, never POSTs.
            if time.monotonic() >= deadline:
                raise TimeoutError("Container did not become ready") from None
            time.sleep(0.25)


def run(base_url: str) -> dict[str, Any]:
    origin = urlsplit(base_url)
    if (
        origin.scheme != "http"
        or origin.hostname != "127.0.0.1"
        or origin.username
        or origin.password
        or origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
    ):
        raise ValueError("Container smoke accepts only a loopback HTTP origin")
    base_url = base_url.rstrip("/")

    def request(path: str, *, post: bool = False, payload: dict[str, str] | None = None) -> Any:
        req = urllib.request.Request(
            base_url + path,
            data=json.dumps(payload).encode() if payload is not None else b"" if post else None,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = response.read(2_000_000)
        return json.loads(data) if path != "/" else data.decode()

    health = wait_for_health(lambda: request("/api/health"))
    validate_health(health)
    if '<div id="root">' not in request("/"):
        raise ValueError("Built frontend was not served")
    results = {}
    for fixture, expected in (("correct", "PASS"), ("incorrect", "FAIL")):
        identifier = request("/api/jobs/demo/" + fixture, post=True)["id"]
        deadline = time.monotonic() + 40
        while True:
            job = request("/api/jobs/" + identifier)
            if job["status"] in {"completed", "failed", "expired"}:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Container fixture job did not finish")
            time.sleep(0.1)
        if job["status"] != "completed" or job["result"]["verdict"] != expected:
            raise ValueError("Container fixture evaluation failed: " + fixture)
        if job["mode"] != "fixture" or job["sam_used"] or job["inference_usage"]:
            raise ValueError("Container smoke dispatched an unexpected provider")
        if not job["result"]["evidence"]:
            raise ValueError("Container fixture result lacks timestamped evidence")
        with urllib.request.urlopen(base_url + job["media_url"], timeout=3) as response:
            if response.headers.get_content_type() != "video/mp4" or not response.read(1):
                raise ValueError("Container playback is unavailable")
        results[fixture] = expected
        history_path = f"/api/jobs/{identifier}/evaluations"
        if len(request(history_path)) != 1:
            raise ValueError("Original container evaluation history is unavailable")
        revised = request(history_path, payload={"procedure": "Ensure the object is sterile."})
        if revised["result"]["verdict"] != "UNKNOWN" or revised["inference_usage"]:
            raise ValueError("Offline re-evaluation did not preserve unsupported uncertainty")
        if len(request(history_path)) != 2:
            raise ValueError("Revised evaluation was not persisted")
        if request(f"/api/jobs/{identifier}")["result"]["verdict"] != expected:
            raise ValueError("Re-evaluation changed the original container verdict")
    ledger = request("/api/costs")
    if ledger["committed_microusd"] != 0:
        raise ValueError("Offline container smoke unexpectedly reserved cost")
    # Exercise the container's actual decoder/normalizer, not only copied fixtures.
    boundary = "reality-compiler-offline-smoke"
    fields = {
        "procedure": "Ensure the object is sterile.",
        "perception_mode": "local_cv",
        "footage_origin": "generated",
    }
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        for key, value in fields.items()
    )
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="video"; '
        'filename="synthetic.mp4"\r\nContent-Type: video/mp4\r\n\r\n'
    ).encode() + (Path(__file__).resolve().parents[1] / "fixtures/correct.mp4").read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    upload = urllib.request.Request(
        base_url + "/api/jobs/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(upload, timeout=10) as response:
        identifier = json.load(response)["id"]
    deadline = time.monotonic() + 60
    while True:
        job = request("/api/jobs/" + identifier)
        if job["status"] in {"completed", "failed", "expired"}:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("Container normalization did not finish")
        time.sleep(0.1)
    if job["status"] != "completed" or job["result"]["verdict"] != "UNKNOWN":
        raise ValueError("Container unsupported upload did not preserve UNKNOWN")
    timing = job["media_metadata"]["source_timing"]
    if timing["frames"][0]["source_index"] != 0 or timing["frames"][0]["source_pts"] != 0:
        raise ValueError("Container source timing provenance unavailable")
    with urllib.request.urlopen(
        base_url + f"/api/jobs/{identifier}/source-frames/0", timeout=30
    ) as response:
        if response.headers.get_content_type() != "image/png" or not response.read(8).startswith(
            b"\x89PNG"
        ):
            raise ValueError("Container exact source frame unavailable")
    if request("/api/costs")["committed_microusd"] != 0 or job["inference_usage"]:
        raise ValueError("Container upload unexpectedly dispatched paid inference")
    return {
        "frontend": "served",
        "fixtures": results,
        "source_mapping": "verified",
        "unsupported_upload": "UNKNOWN",
        "paid_inference": False,
        "cost_microusd": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    print(json.dumps(run(parser.parse_args().base_url)))


if __name__ == "__main__":
    main()
