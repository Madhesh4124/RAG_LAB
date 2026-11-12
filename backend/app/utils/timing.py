import threading
import time
from typing import Dict, Tuple


class PipelineTimer:
    def __init__(self):
        self._lock = threading.RLock()
        self._start_times: Dict[Tuple[int, str], float] = {}
        self._durations: Dict[str, float] = {}

    def start(self, stage_name: str) -> None:
        """Starts the timer for a specified stage on the current thread."""
        key = (threading.get_ident(), stage_name)
        with self._lock:
            self._start_times[key] = time.perf_counter()

    def stop(self, stage_name: str) -> None:
        """Stops the timer for a stage and calculates duration in milliseconds."""
        key = (threading.get_ident(), stage_name)
        with self._lock:
            started_at = self._start_times.pop(key, None)
            if started_at is None:
                # Fallback if start/stop happened across threads cleanly: pop matching stage if unique.
                for candidate_key in list(self._start_times.keys()):
                    if candidate_key[1] == stage_name:
                        started_at = self._start_times.pop(candidate_key)
                        break
            if started_at is None:
                return

            elapsed_sec = time.perf_counter() - started_at
            self._durations[stage_name] = elapsed_sec * 1000.0

    def get_timings(self) -> Dict[str, float]:
        """Returns a dict of all stage names to their duration in milliseconds."""
        with self._lock:
            return self._durations.copy()

    def get_total_ms(self) -> float:
        """Returns the sum of all recorded stage durations as a float."""
        with self._lock:
            return sum(self._durations.values())

    def to_metrics_dict(self) -> Dict[str, float]:
        """Returns a dict mapping directly to the Metrics model fields."""
        with self._lock:
            return {
                "chunking_time_ms": self._durations.get("chunking_time_ms", 0.0),
                "embedding_time_ms": self._durations.get("embedding_time_ms", 0.0),
                "retrieval_time_ms": self._durations.get("retrieval_time_ms", 0.0),
                "reranking_time_ms": self._durations.get("reranking_time_ms", 0.0),
                "llm_time_ms": self._durations.get("llm_time_ms", 0.0),
                "total_time_ms": sum(self._durations.values()),
            }

    def reset(self) -> None:
        """Clears all recorded timings and currently running timers."""
        with self._lock:
            self._start_times.clear()
            self._durations.clear()
