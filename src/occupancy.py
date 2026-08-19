"""
occupancy.py
------------
Occupancy engine. Deliberately has zero knowledge of detection, tracking,
or how a crossing was decided — it only consumes CrossingEvent objects and
maintains a running count. This isolation means the same engine can sit
underneath the baseline OR a future confidence-aware method unchanged; only
the events feeding it would differ.
"""

from dataclasses import dataclass


@dataclass
class OccupancySnapshot:
    frame: int
    timestamp: float
    occupancy: int
    max_occupancy_so_far: int


class OccupancyEngine:
    def __init__(self, initial_occupancy: int = 0, clamp_minimum_zero: bool = True):
        self.occupancy = initial_occupancy
        self.clamp_minimum_zero = clamp_minimum_zero
        self.max_occupancy_so_far = initial_occupancy
        self.total_entries = 0
        self.total_exits = 0

    def apply_event(self, direction: str) -> int:
        """Apply a single IN/OUT event and return the new occupancy value."""
        if direction == "IN":
            self.occupancy += 1
            self.total_entries += 1
        elif direction == "OUT":
            self.occupancy -= 1
            self.total_exits += 1
        else:
            raise ValueError(f"Unknown direction: {direction}")

        if self.clamp_minimum_zero and self.occupancy < 0:
            self.occupancy = 0

        self.max_occupancy_so_far = max(self.max_occupancy_so_far, self.occupancy)
        return self.occupancy

    def snapshot(self, frame: int, timestamp: float) -> OccupancySnapshot:
        return OccupancySnapshot(
            frame=frame,
            timestamp=timestamp,
            occupancy=self.occupancy,
            max_occupancy_so_far=self.max_occupancy_so_far,
        )
