"""
tracking.py
-----------
Multi-object tracking module. Wraps two tracker backends from the
standalone `trackers` package (Roboflow) — ByteTrack and BoT-SORT — behind
one common interface, selected by config (`tracker.type`). No source code
change is needed to switch trackers.

This is a separate module from detection.py by design: it receives already-
computed detections for a frame and returns the same detections annotated
with persistent tracker_id values. Nothing outside this file needs to know
which tracker backend is active.

No original tracking algorithm is implemented here — this is a thin,
documented wrapper. ByteTrack is based on Zhang et al.'s reference
implementation; BoT-SORT is based on Aharon et al.'s reference
implementation. Both are used here via Roboflow's `trackers` package.

Key difference between the two backends that this module accounts for:
BoT-SORT optionally uses Camera Motion Compensation (CMC), which needs the
raw frame image (not just detections) to estimate camera movement between
frames. ByteTrack has no such mechanism and does not accept a frame argument.
This module hides that difference from callers — `update()` always accepts
a frame, and only forwards it to the tracker that actually uses it.

IMPORTANT: tracker_id == -1 means "not yet a confirmed, stable track" (the
tracker needs a configurable number of consecutive matched frames before
promoting a candidate to a real ID). Downstream modules (line_crossing.py)
filter these out before using them for crossing logic.
"""

import supervision as sv
from trackers import ByteTrackTracker, BoTSORTTracker

_TRACKER_CLASSES = {
    "bytetrack": ByteTrackTracker,
    "botsort": BoTSORTTracker,
}

# Trackers whose update() call actually consumes the frame image (for
# camera motion compensation or similar). Everything else ignores it.
_FRAME_CONSUMING_TRACKERS = {"botsort"}


class PersonTracker:
    def __init__(self, tracker_type: str, params: dict, frame_rate: float):
        if tracker_type not in _TRACKER_CLASSES:
            raise ValueError(
                f"Unknown tracker type: {tracker_type!r}. Supported: {list(_TRACKER_CLASSES)}"
            )
        self.tracker_type = tracker_type
        self._tracker_class = _TRACKER_CLASSES[tracker_type]
        self._init_kwargs = {**params, "frame_rate": frame_rate}
        self.tracker = self._tracker_class(**self._init_kwargs)

    def update(self, detections: sv.Detections, frame=None, timestamp: float = None) -> sv.Detections:
        """
        Feed one frame's detections into the active tracker.
        Returns detections with a `.tracker_id` field populated. IDs of -1
        mean "not yet a confirmed track".
        """
        if self.tracker_type in _FRAME_CONSUMING_TRACKERS:
            return self.tracker.update(detections, frame=frame, timestamp=timestamp)
        return self.tracker.update(detections, timestamp=timestamp)

    def reset(self):
        """Reset all track state — used between separate video runs."""
        self.tracker = self._tracker_class(**self._init_kwargs)
