#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import get_session

ROOT = Path(__file__).resolve().parents[1]


def _inject_backend_path() -> None:
    backend_path = ROOT / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 6 deterministic multi-layer semantic precompute pipeline.",
    )
    parser.add_argument(
        "--business-id",
        action="append",
        type=int,
        default=[],
        help="Business id to process (can be passed multiple times).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max businesses to process when ids are not provided.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _inject_backend_path()

    from app.services.phase6.pipeline import Phase6PrecisionPipeline

    session = get_session()
    pipeline = Phase6PrecisionPipeline()
    try:
        stats = pipeline.run(
            session=session,
            business_ids=args.business_id,
            limit=args.limit,
        )
        session.commit()
        print(
            "Phase 6 precision pipeline complete: "
            f"businesses_processed={stats.businesses_processed}, "
            f"claims_mapped={stats.claims_mapped}, "
            f"claims_verified={stats.claims_verified}"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
