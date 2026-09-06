# System Specification — Frozen Baseline

Technical reference for the implementation as it exists in this
repository. Describes what the code does, not what it could do.

## 1. Architecture

```
Video (cv2.VideoCapture)
  -> PersonDetector.detect(frame) -> sv.Detections
  -> PersonTracker.update(detections, frame, timestamp) -> sv.Detections with tracker_id
  -> LineCrossingDetector.update(tracked_detections) -> list[CrossingEvent]
  -> OccupancyEngine.apply_event(direction) -> int (new occupancy)
  -> EventLogger.log_event(...) / log_timeline(...)
```

`src/main.py` contains only this orchestration loop — frame read, call
each module in order, write annotated frame if enabled, print a summary.
It implements no detection, tracking, counting, or validation logic.

## 2. Modules

### `detection.py` — `PersonDetector`
Thin wrapper around `ultralytics.YOLO`. Calls `model.predict()` per frame
(never `model.track()`), passing confidence threshold, IoU threshold,
target class list, and inference image size from config. Returns
`supervision.Detections` via `sv.Detections.from_ultralytics(results)`.

### `tracking.py` — `PersonTracker`
Wraps `ByteTrackTracker` and `BoTSORTTracker` from the standalone
`trackers` package behind one interface, selected by `tracker_type` at
construction. `update()` always accepts a `frame` argument but only
forwards it to trackers in `_FRAME_CONSUMING_TRACKERS` (currently just
`"botsort"`, which uses the frame for Camera Motion Compensation).
`tracker_id == -1` denotes an unconfirmed track. `reset()` reconstructs
the tracker from its original init kwargs — provided for batch use
between separate videos, not called by `main.py`.

### `line_crossing.py` — `LineCrossingDetector`
Wraps `supervision.LineZone` with `triggering_anchors=[sv.Position.BOTTOM_CENTER]`.
Line endpoints are supplied in normalized coordinates and converted to
pixel coordinates using the frame's actual width/height at construction.
Before calling `line_zone.trigger()`, detections with `tracker_id == -1`
are dropped (comment in source: "tracking-hygiene fix... part of the
frozen baseline", not part of any validation method). For each detection
crossing the line this frame, emits a `CrossingEvent(tracker_id, direction,
confidence, bbox)`. `direction` is derived from Supervision's raw
`crossed_in`/`crossed_out` boolean arrays, remapped through
`in_is_downward` to a semantic "IN"/"OUT" label. No persistence, no
confidence gate beyond what already passed through detection, no
duplicate-crossing suppression.

### `occupancy.py` — `OccupancyEngine`
Holds `occupancy`, `max_occupancy_so_far`, `total_entries`,
`total_exits`. `apply_event("IN")` increments, `apply_event("OUT")`
decrements, then clamps to a minimum of 0 if `clamp_minimum_zero` is set.
Has no dependency on detection, tracking, or CV libraries at all —
verified by inspecting its imports (`dataclasses` only).

### `event_logger.py` — `EventLogger`
Opens two CSV files per run under `<output_dir>/logs/`:
`<experiment_id>_events.csv` (header: `frame, timestamp_sec, track_id,
detection_confidence, crossing_direction, predicted_event,
occupancy_after_event`) and `<experiment_id>_occupancy_timeline.csv`
(header: `frame, timestamp_sec, occupancy, max_occupancy_so_far`).
`_non_clobbering_path()` appends a numeric suffix (`_1`, `_2`, ...) if a
file for that `experiment_id` already exists, so prior runs are never
overwritten. Both files are flushed after every write.

### `config_loader.py` — `load_config`, `freeze_config_copy`
Parses YAML into typed dataclasses (`PipelineConfig` and nested configs
for video/detection/tracker/line/occupancy/logging). Raises
`ValueError` if any required top-level section is missing. `TrackerConfig.active_params()`
returns only the parameter block matching the active `type`, raising on
an unrecognized tracker type. `freeze_config_copy()` copies the exact
config file used into `<output_dir>/raw/<experiment_id>_config_used.yaml`
so every result can be traced back to the parameters that produced it.

### `evaluation.py` — `evaluate`, `save_evaluation_csv`
Standalone script/module, not called from `main.py`. Reads the events and
timeline CSVs produced by a run, plus a ground-truth CSV in the format
documented in the module docstring (columns: `frame, actual_entry,
actual_exit, actual_occupancy`). Supports sparse ground truth (only
entry/exit moments) via forward-filling from `initial_occupancy`, or
dense ground truth (`actual_occupancy` populated on every relevant row),
with dense values taking precedence. Computes, per direction (entry/exit):
true positives / false positives / false negatives via greedy nearest-frame
matching within a configurable tolerance (default 15 frames), then
precision/recall/F1. Computes occupancy MAE and max absolute error against
the ground-truth occupancy series at every frame the predicted timeline
covers. Any metric it cannot compute from available data is reported with
an explanatory note in the `notes` field, never estimated.

## 3. Data Flow / I/O Contracts

- **Input:** one video file (path from `video.source`), read via
  `cv2.VideoCapture`. FPS/width/height/frame-count are read from the video
  itself, not assumed.
- **Config → results traceability:** every executed run's exact YAML is
  copied into `results/raw/`.
- **Output:** events CSV, occupancy-timeline CSV, optional annotated MP4.
  All three live under the `logging.output_dir` from config, resolved
  relative to wherever `main.py` is invoked from (documented as `src/`).
- **Evaluation (optional):** consumes the events + timeline CSVs from a
  run plus an external ground-truth CSV; produces a single-row evaluation
  CSV via `save_evaluation_csv`.

## 4. Configuration Schema

Required top-level YAML keys (enforced by `config_loader.load_config`):
`experiment`, `video`, `detection`, `tracker`, `line`, `occupancy`,
`logging`. See `docs/PAPER_FACTS.md` for the full field list with types,
and the tracked config files in `config/` for real examples of each
field populated.

## 5. Assumptions Baked Into the Frozen Baseline

- A person's bounding box is assumed to transition from one side of the
  line to the other within a small number of frames; very wide bounding
  boxes relative to frame width (close camera placement) are known to
  break `LineZone`'s crossing detection (documented previously in this
  project's README as the reason recording guidance recommends keeping a
  bounding box under roughly 25–30% of frame width — this specific
  guidance could not be re-verified against a currently-tracked video in
  this repository, since the `V00` clip it was based on is not present;
  see `PAPER_TODO.md`).
- `in_is_downward`'s correct value is camera-setup-specific and must be
  verified empirically per line/camera combination — it is not derived
  automatically.
- The pipeline assumes deterministic tracker/detector behavior across
  reruns of the same config and video. This assumption is **contradicted**
  by the `vcamtesting_bytetrack` experiment (see `docs/EXPERIMENTS.md`)
  and needs investigation before results from this experiment are used
  in any quantitative claim.

## 6. Evaluation Method (as implemented, not as could be extended)

Event matching is one-to-one and greedy: for each predicted event frame,
the nearest unmatched ground-truth event frame within tolerance is
claimed as a match; unmatched predictions are false positives, unmatched
ground-truth events are false negatives. This is a simple frame-tolerance
matching scheme — it does not account for direction confusion beyond
already splitting entries and exits into separate matching passes, and it
has not been exercised against any real ground-truth data in this
repository yet.

## 7. Limitations (technical, from code inspection only)

See the README's "Limitations" section and `docs/EXPERIMENTS.md`'s
per-experiment flags — not duplicated here to avoid drift between the two
documents.
