from __future__ import annotations

import logging

PERF_LEVEL_NUM = 25
PERF_LEVEL_NAME = "PERF"


def _perf(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(PERF_LEVEL_NUM):
        self._log(PERF_LEVEL_NUM, message, args, **kwargs)


def register_perf_level() -> None:
    if logging.getLevelName(PERF_LEVEL_NUM) != PERF_LEVEL_NAME:
        logging.addLevelName(PERF_LEVEL_NUM, PERF_LEVEL_NAME)

    if not hasattr(logging.Logger, "perf"):
        setattr(logging.Logger, "perf", _perf)


def resolve_log_level(value: str | None, fallback: int = logging.INFO) -> int:
    if not value:
        return fallback
    normalized = value.strip().upper()
    if normalized == PERF_LEVEL_NAME:
        return PERF_LEVEL_NUM
    resolved = logging.getLevelName(normalized)
    if isinstance(resolved, int):
        return resolved
    return fallback


def configure_logging(app_level: str, perf_level: str) -> None:
    register_perf_level()
    app_log_level = resolve_log_level(app_level, fallback=logging.INFO)
    perf_log_level = resolve_log_level(perf_level, fallback=PERF_LEVEL_NUM)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=app_log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root.setLevel(app_log_level)

    logging.getLogger("buycott.perf").setLevel(perf_log_level)
