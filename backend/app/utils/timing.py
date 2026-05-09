import time
from typing import Dict


class PipelineTimer:
    def __init__(self):
        self._start_times: Dict[str, float] = {}
        self._durations: Dict[str, float] = {}

    def start(self, stage_name: str) -> None:
        """Starts the timer for a specified stage."""
        self._start_times[stage_name] = time.perf_counter()

    def stop(self, stage_name: str) -> None:
        """Stops the timer for a stage and calculates duration in milliseconds."""
        if stage_name not in self._start_times:
            # P3.4: Be resilient to missing start calls instead of crashing the request.
            # This can happen if the pipeline is used concurrently without proper isolation.
            return

        end_time = time.perf_counter()
        elapsed_sec = end_time - self._start_times.pop(stage_name)
        self._durations[stage_name] = elapsed_sec * 1000.0

    def get_timings(self) -> Dict[str, float]:
        """Returns a dict of all stage names to their duration in milliseconds."""
        return self._durations.copy()

    def get_total_ms(self) -> float:
        """Returns the sum of all recorded stage durations as a float."""
        return sum(self._durations.values())

    def to_metrics_dict(self) -> Dict[str, float]:
        """Returns a dict mapping directly to the Metrics model fields."""
        return {
            "chunking_time_ms": self._durations.get("chunking_time_ms", 0.0),
            "embedding_time_ms": self._durations.get("embedding_time_ms", 0.0),
            "retrieval_time_ms": self._durations.get("retrieval_time_ms", 0.0),
            "reranking_time_ms": self._durations.get("reranking_time_ms", 0.0),
            "llm_time_ms": self._durations.get("llm_time_ms", 0.0),
            "total_time_ms": self.get_total_ms()
        }

    def reset(self) -> None:
        """Clears all recorded timings and currently running timers."""
        self._start_times.clear()
        self._durations.clear()