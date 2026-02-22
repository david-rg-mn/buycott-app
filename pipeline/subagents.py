#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json

from openclaw.runtime import (
    RetryingHttpClient,
    SourceCandidate,
    build_scraper_registry,
    ensure_docker_sandbox,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenClaw sub-agent runner")
    sub = parser.add_subparsers(dest="command", required=True)

    spawn = sub.add_parser("spawn", help="Run a specific scraper sub-agent against one source URL")
    spawn.add_argument(
        "agent",
        choices=(
            "html-scraper",
            "spa-scraper",
            "pdf-scraper",
            "ocr-scraper",
            "api-scraper",
            "social-scraper",
        ),
    )
    spawn.add_argument("--source-url", required=True)
    spawn.add_argument("--source-type", default="website")
    spawn.add_argument("--source-snippet", default="")
    spawn.add_argument("--allow-host-execution", action="store_true")
    return parser.parse_args()


def _agent_to_modality(agent_name: str) -> str:
    mapping = {
        "html-scraper": "html",
        "spa-scraper": "spa",
        "pdf-scraper": "pdf",
        "ocr-scraper": "image",
        "api-scraper": "api",
        "social-scraper": "social",
    }
    return mapping[agent_name]


def _to_jsonable(value):
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def main() -> None:
    args = _parse_args()
    if args.command != "spawn":
        raise RuntimeError("Unsupported command")

    ensure_docker_sandbox(allow_host_execution=args.allow_host_execution)
    modality = _agent_to_modality(args.agent)
    source = SourceCandidate(
        source_url=args.source_url,
        source_type=args.source_type,
        source_snippet=args.source_snippet,
    )

    client = RetryingHttpClient(timeout_seconds=30.0, max_attempts=4, base_backoff_seconds=1.0)
    try:
        registry = build_scraper_registry(client)
        scraper = registry[modality]
        result = scraper.run(source)
        print(json.dumps(_to_jsonable(result), indent=2, ensure_ascii=True))
    finally:
        client.close()


if __name__ == "__main__":
    main()
