from __future__ import annotations

from app.db.models import Business
from app.phase0_identity_lock.constraints import FORBIDDEN_SCHEMA_FIELDS


def assert_schema_invariants() -> None:
    business_fields = set(Business.__table__.columns.keys())
    violations = sorted(FORBIDDEN_SCHEMA_FIELDS.intersection(business_fields))
    if violations:
        raise RuntimeError(
            "Phase 0 schema invariant violated: forbidden fields present -> "
            + ", ".join(violations)
        )
