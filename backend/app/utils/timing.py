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
            raise ValueError(f"Timer for stage '{stage_name}' was never started.")
            
        end_time = time.perf_counter()
        elapsed_sec = end_time - self._start_times.pop(stage_name)
        
        # Convert seconds to milliseconds
        self._durations[stage_name] = elapsed_sec * 1000.0
        
    def get_timings(self) -> Dict[str, float]:
        """Returns a dict of all stage names to their duration in milliseconds."""
        return self._durations.copy()
        
    def reset(self) -> None:
        """Clears all recorded timings and currently running timers."""
        self._start_times.clear()
        self._durations.clear()
