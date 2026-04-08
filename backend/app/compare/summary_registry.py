from __future__ import annotations

import threading
from typing import Optional

_SUMMARY_CACHE: dict[str, str] = {}
_SUMMARY_LOCK = threading.Lock()


def get_summary(summary_key: str) -> Optional[str]:
    with _SUMMARY_LOCK:
        return _SUMMARY_CACHE.get(summary_key)


def set_summary(summary_key: str, summary: str) -> None:
    with _SUMMARY_LOCK:
        _SUMMARY_CACHE[summary_key] = summary


def has_summary(summary_key: str) -> bool:
    with _SUMMARY_LOCK:
        return summary_key in _SUMMARY_CACHE


def clear_summary_registry() -> None:
    with _SUMMARY_LOCK:
        _SUMMARY_CACHE.clear()