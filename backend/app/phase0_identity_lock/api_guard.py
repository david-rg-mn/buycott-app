from fastapi import HTTPException, Request, status

from app.phase0_identity_lock.constraints import FORBIDDEN_API_PARAMS


def enforce_identity_lock(request: Request) -> None:
    forbidden = [param for param in request.query_params.keys() if param in FORBIDDEN_API_PARAMS]
    if forbidden:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Phase 0 identity lock violation: forbidden API parameters detected "
                f"{', '.join(sorted(forbidden))}."
            ),
        )
