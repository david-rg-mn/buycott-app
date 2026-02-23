#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_REQUIRED_MODULES = ("sqlalchemy", "numpy", "psycopg", "pgvector", "httpx")
DOCKER_PIPELINE_ROOT = "/workspace/pipeline"


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _missing_local_modules() -> list[str]:
    return [module_name for module_name in LOCAL_REQUIRED_MODULES if not _module_available(module_name)]


def _running_compose_services() -> set[str]:
    cmd = ["docker", "compose", "ps", "--status", "running", "--services"]
    try:
        result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return set()

    if result.returncode != 0:
        return set()

    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _resolve_mode(mode: str) -> str:
    missing_modules = _missing_local_modules()
    running_services = _running_compose_services()

    if mode == "local":
        if missing_modules:
            missing = ", ".join(missing_modules)
            raise RuntimeError(
                f"Local mode requires Python packages not found: {missing}. "
                "Install them with `python3 -m pip install -r backend/requirements.txt`, "
                "or run with `--mode docker`."
            )
        return "local"

    if mode == "docker":
        if "api" not in running_services:
            raise RuntimeError(
                "Docker mode requires the `api` compose service to be running. "
                "Start it with `docker compose up --build -d`."
            )
        return "docker"

    if not missing_modules:
        return "local"

    if "api" in running_services:
        missing = ", ".join(missing_modules)
        print(f"Local Python packages missing ({missing}). Falling back to Docker mode.")
        return "docker"

    missing = ", ".join(missing_modules)
    raise RuntimeError(
        "Unable to run pipeline in auto mode. "
        f"Missing local Python packages: {missing}. "
        "Install dependencies with `python3 -m pip install -r backend/requirements.txt`, "
        "or start Docker with `docker compose up --build -d`."
    )


def _run(script_name: str, mode: str, extra_args: list[str] | None = None) -> None:
    extra_args = extra_args or []
    if mode == "local":
        script_path = ROOT / "pipeline" / script_name
        cmd = [sys.executable, str(script_path), *extra_args]
    else:
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            f"{DOCKER_PIPELINE_ROOT}/{script_name}",
            *extra_args,
        ]

    print(f"Running ({mode}): {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Buycott Google Places + embedding + capability pipeline")
    parser.add_argument("--with-schema", action="store_true", help="Apply database/schema.sql before loading data")
    parser.add_argument(
        "--seed-google",
        action="store_true",
        help="Run Google Places ingestion for Powderhorn before embeddings",
    )
    parser.add_argument(
        "--seed-google-force-refresh",
        action="store_true",
        help="Force Google Places refresh even when existing records are within TTL.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "local", "docker"),
        default="auto",
        help="Execution mode: local Python env, Docker Compose API container, or auto-detect",
    )
    parser.add_argument(
        "--phase5-openclaw",
        action="store_true",
        help="Run Phase 5 OpenClaw multi-agent enrichment from Google place/business sources.",
    )
    parser.add_argument(
        "--phase5-place-id",
        action="append",
        default=[],
        help="Optional Google Place ID filter for Phase 5 (can be used multiple times).",
    )
    parser.add_argument(
        "--phase5-limit",
        type=int,
        default=None,
        help="Optional max businesses to process in Phase 5 when ids are not provided.",
    )
    parser.add_argument(
        "--phase5-allow-host-execution",
        action="store_true",
        help="Override Docker sandbox enforcement for Phase 5 (not recommended).",
    )
    parser.add_argument(
        "--phase6-precision",
        action="store_true",
        help="Run Phase 6 deterministic multi-layer semantic indexing pipeline.",
    )
    parser.add_argument(
        "--phase6-business-id",
        action="append",
        type=int,
        default=[],
        help="Optional business id filter for Phase 6 (can be used multiple times).",
    )
    parser.add_argument(
        "--phase6-limit",
        type=int,
        default=None,
        help="Optional max businesses to process in Phase 6 when ids are not provided.",
    )
    parser.add_argument(
        "--rebuild-business-model",
        action="store_true",
        help="Backfill and normalize Places-only business_model payloads for all businesses.",
    )
    parser.add_argument(
        "--rebuild-business-model-limit",
        type=int,
        default=None,
        help="Optional max businesses for business_model backfill.",
    )
    args = parser.parse_args()

    try:
        mode = _resolve_mode(args.mode)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.with_schema:
        _run("init_db.py", mode)

    if args.seed_google:
        seed_args: list[str] = []
        if args.seed_google_force_refresh:
            seed_args.append("--force-refresh")
        _run("google_places_seed.py", mode, seed_args)
    if args.rebuild_business_model:
        rebuild_args: list[str] = []
        if args.rebuild_business_model_limit is not None:
            rebuild_args.extend(["--limit", str(args.rebuild_business_model_limit)])
        _run("rebuild_business_models.py", mode, rebuild_args)
    if args.phase5_openclaw:
        phase5_args: list[str] = []
        for place_id in args.phase5_place_id:
            phase5_args.extend(["--google-place-id", place_id])
        if args.phase5_limit is not None:
            phase5_args.extend(["--limit", str(args.phase5_limit)])
        if args.phase5_allow_host_execution:
            phase5_args.append("--allow-host-execution")
        _run("phase5_openclaw_pipeline.py", mode, phase5_args)
    if args.phase6_precision:
        phase6_args: list[str] = []
        for business_id in args.phase6_business_id:
            phase6_args.extend(["--business-id", str(business_id)])
        if args.phase6_limit is not None:
            phase6_args.extend(["--limit", str(args.phase6_limit)])
        _run("phase6_precision_pipeline.py", mode, phase6_args)
    _run("build_embeddings.py", mode)
    _run("rebuild_capabilities.py", mode)
    print("Pipeline completed")


if __name__ == "__main__":
    main()
