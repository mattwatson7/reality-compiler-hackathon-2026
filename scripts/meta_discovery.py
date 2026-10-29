"""Explicit non-inference Meta catalog check. Never prints credentials or raw bodies."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.meta import MODEL_IDS, MetaClient, MetaContractError, MetaDisabled, load_key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result: dict[str, object] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "endpoint": "GET https://api.meta.ai/v1/models",
        "inference_requests": 0,
        "api_spend_microusd": 0,
        "credential_present": bool(load_key().get_secret_value()),
        "authenticated": False,
        "models": [],
    }
    try:
        catalog = MetaClient(key=load_key()).discover()
        result.update(
            authenticated=catalog.authenticated,
            models=[m for m in MODEL_IDS if catalog.supports(m)],
        )
    except (MetaContractError, MetaDisabled) as exc:
        result["error"] = str(exc)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["authenticated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
