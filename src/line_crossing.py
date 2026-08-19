"""
line_crossing.py
-----------------
Conventional virtual-line crossing detection for the BASELINE system.

Wraps Supervision's LineZone utility. Given a line defined in the config
(normalized coordinates, two endpoints — can represent ANY orientation:
horizontal, vertical, or diagonal) and a stream of tracked detections, this
module reports raw IN/OUT crossing candidates for each track — with no
confidence filtering, persistence checks, or trajectory validation. That
validation logic belongs to the (not-yet-implemented) proposed method.

LINE DEFINITION
---------------
The line is defined by two endpoints (x1,y1)-(x2,y2) in NORMALIZED
coordinates (0.0-1.0, relative to frame width/height), so the same config
works across different video resolutions. Because it's just two points,
the line can be:
  - horizontal   (y1 == y2)   e.g. a line across a hallway viewed from above
  - vertical     (x1 == x2)   e.g. a line at a fixed x-position, full height
  - diagonal     (general case)

`in_is_downward` is a semantic label, not a geometric constraint: it just
tells the pipeline which of Supervision's two raw crossing signals
(crossed_in / crossed_out) should be reported as our "IN" label. For a
vertical line this name is a slight misnomer (nothing moves "downward") —
it still functions correctly, it simply swaps which raw signal means IN
vs OUT. Determine the correct value for a given line/camera setup
empirically (run once, check the annotated video and CSV, flip if reversed)
rather than assuming.

TRACK CONFIRMATION FILTERING
-----------------------------
Detections with an unconfirmed tracker_id (-1) are dropped before reaching
the line zone. Feeding -1-ID detections in would let unrelated people share
the same "track" for crossing purposes, corrupting the line zone's internal
per-ID crossing state and producing spurious IN/OUT events. This filtering
is a tracking-hygiene fix, not part of any confidence-aware validation
method — it is part of the frozen baseline.
"""

import supervision as sv
from dataclasses import dataclass


@dataclass
class CrossingEvent:
    tracker_id: int
    direction: str          # "IN" or "OUT"
    confidence: float
    bbox: tuple              # (x1, y1, x2, y2) at the moment of crossing


class LineCrossingDetector:
    def __init__(self, x1_norm: float, y1_norm: float, x2_norm: float, y2_norm: float,
                 in_is_downward: bool, frame_width: int, frame_height: int):
        self.in_is_downward = in_is_downward

        start = sv.Point(x=x1_norm * frame_width, y=y1_norm * frame_height)
        end = sv.Point(x=x2_norm * frame_width, y=y2_norm * frame_height)

        self.line_zone = sv.LineZone(start=start, end=end)

        self.line_pixel_coords = {
            "x1": start.x, "y1": start.y, "x2": end.x, "y2": end.y
        }

    def update(self, detections: sv.Detections) -> list:
        """
        Feed one frame's tracked detections through the line zone.
        Returns a list of CrossingEvent objects for any track that crossed
        the line THIS frame (conventional, unvalidated crossing — a track
        crossing back and forth will simply generate multiple raw events;
        the baseline does not protect against this by design).
        """
        if detections.tracker_id is not None:
            confirmed_mask = detections.tracker_id != -1
            detections = detections[confirmed_mask]

        if len(detections) == 0:
            return []

        crossed_in, crossed_out = self.line_zone.trigger(detections)

        events = []
        for i in range(len(detections)):
            tracker_id = int(detections.tracker_id[i]) if detections.tracker_id is not None else None
            confidence = float(detections.confidence[i]) if detections.confidence is not None else None
            bbox = tuple(detections.xyxy[i].tolist())

            if crossed_in[i]:
                direction = "IN" if self.in_is_downward else "OUT"
                events.append(CrossingEvent(tracker_id, direction, confidence, bbox))
            elif crossed_out[i]:
                direction = "OUT" if self.in_is_downward else "IN"
                events.append(CrossingEvent(tracker_id, direction, confidence, bbox))

        return events
