"""
event_logger.py
----------------
Handles all CSV logging. Two logs are produced per run:

1. <experiment_id>_events.csv
   One row per accepted crossing event: frame, timestamp, track ID,
   detection confidence, direction, predicted event, occupancy after event.

2. <experiment_id>_occupancy_timeline.csv
   One row per processed frame, giving occupancy over time — needed for
   "actual vs predicted occupancy over time" plots and for evaluation.py.

Rule enforced here: raw experiment data is never overwritten. If an output
file for this experiment_id already exists, a numeric suffix is appended
rather than silently clobbering prior results.
"""

import csv
from pathlib import Path


class EventLogger:
    def __init__(self, output_dir: str, experiment_id: str):
        self.logs_dir = Path(output_dir) / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.events_path = self._non_clobbering_path(f"{experiment_id}_events.csv")
        self.timeline_path = self._non_clobbering_path(f"{experiment_id}_occupancy_timeline.csv")

        self._events_file = open(self.events_path, "w", newline="")
        self._events_writer = csv.writer(self._events_file)
        self._events_writer.writerow([
            "frame", "timestamp_sec", "track_id", "detection_confidence",
            "crossing_direction", "predicted_event", "occupancy_after_event"
        ])

        self._timeline_file = open(self.timeline_path, "w", newline="")
        self._timeline_writer = csv.writer(self._timeline_file)
        self._timeline_writer.writerow([
            "frame", "timestamp_sec", "occupancy", "max_occupancy_so_far"
        ])

    def _non_clobbering_path(self, filename: str) -> Path:
        path = self.logs_dir / filename
        if not path.exists():
            return path
        stem, suffix = path.stem, path.suffix
        i = 1
        while True:
            candidate = self.logs_dir / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def log_event(self, frame: int, timestamp: float, track_id: int, confidence: float,
                  direction: str, occupancy_after: int):
        self._events_writer.writerow([
            frame, round(timestamp, 3), track_id,
            round(confidence, 4) if confidence is not None else "",
            direction, direction, occupancy_after
        ])
        self._events_file.flush()

    def log_timeline(self, frame: int, timestamp: float, occupancy: int, max_occupancy: int):
        self._timeline_writer.writerow([frame, round(timestamp, 3), occupancy, max_occupancy])
        self._timeline_file.flush()

    def close(self):
        self._events_file.close()
        self._timeline_file.close()
