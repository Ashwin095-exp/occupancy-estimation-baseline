# Video-Based Occupancy Estimation via Line-Crossing Counting — Frozen Baseline

## Abstract / Project Summary

This repository implements a conventional line-crossing occupancy counter
for single-camera video: pretrained YOLO person detection feeds a
config-selectable multi-object tracker (ByteTrack or BoT-SORT), tracked
identities are checked against a virtual counting line, and each accepted
crossing increments or decrements a running occupancy count. Results are
logged per-event and per-frame to CSV, with an optional comparison against
a hand-labeled ground-truth CSV.

**This is the frozen baseline.** No confidence filtering beyond the
detector's own threshold, no track-persistence requirement, and no
trajectory or direction-consistency validation is implemented — the
pipeline reports every raw crossing candidate as-is. This exists to (a)
prove the pipeline runs end-to-end and (b) generate reference numbers that
a future validation method would be compared against. No novel algorithm
is claimed at this stage; see "Potential Research Contribution" in
`docs/PAPER_FACTS.md`.

## System Overview

Verified from `src/main.py` and the modules it imports:

```text
Input Video (cv2.VideoCapture)
       │
       ▼
PersonDetector (Ultralytics YOLO, detection only — no model.track())
       │  sv.Detections, filtered by confidence/IoU/class in config
       ▼
PersonTracker (ByteTrackTracker or BoTSORTTracker, from the `trackers`
       │        package — selected by config, no code change needed)
       │  tracker_id == -1 means "not yet confirmed"
       ▼
LineCrossingDetector (wraps supervision.LineZone, BOTTOM_CENTER anchor)
       │  drops unconfirmed (-1) tracks first; reports every raw
       │  IN/OUT crossing, no validation
       ▼
OccupancyEngine (pure counter: +1 on IN, -1 on OUT, optional clamp at 0)
       │
       ├──────────────► events.csv (one row per accepted crossing)
       │
       ├──────────────► occupancy_timeline.csv (one row per processed frame)
       │
       └──────────────► annotated video (boxes, IDs, line, occupancy overlay)
                            │
                            ▼
                    evaluation.py (optional — only if a ground-truth
                                    CSV is supplied; not run for any
                                    experiment in this repo yet, see
                                    docs/PAPER_TODO.md)
```

## Repository Structure

```
occupancy-estimation-baseline/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   ├── baseline_config.yaml              # generic ByteTrack template — placeholder video/line, never run
│   ├── botsort_config.yaml               # generic BoT-SORT template — placeholder video/line, never run
│   ├── v001_botsort_config.yaml          # test_v001.mp4, BoT-SORT, vertical line x=0.7218
│   ├── v001_calibration_config.yaml      # test_v001.mp4, ByteTrack, vertical line x=0.7218
│   └── vcamtesting_bytetrack_config.yaml # vcamtesting.mp4, ByteTrack, horizontal line y=0.7992
├── models/
│   └── yolo11n.pt                        # YOLO weights, auto-downloaded by Ultralytics if absent
├── src/
│   ├── config_loader.py                  # loads/validates YAML, freezes a copy per run
│   ├── detection.py                      # YOLO wrapper — detection ONLY
│   ├── tracking.py                       # ByteTrack / BoT-SORT wrapper, selected by config
│   ├── line_crossing.py                  # conventional, unvalidated line-crossing logic
│   ├── occupancy.py                      # pure counting engine, no CV code
│   ├── event_logger.py                   # CSV logging, never overwrites prior runs
│   ├── evaluation.py                     # compares output to ground truth (not yet exercised — see docs/PAPER_TODO.md)
│   └── main.py                           # orchestrator only, no algorithmic logic of its own
├── data/
│   ├── videos/                           # test_v001.mp4, vcamtesting.mp4, vcamtesting2.mp4
│   └── ground_truth/
│       └── ground_truth_template.csv     # format reference only — no populated ground truth exists yet
├── results/
│   ├── raw/                              # frozen config copy for every run actually executed
│   ├── logs/                             # events + occupancy timeline CSVs
│   ├── annotated/                        # QA videos (boxes/IDs/line/occupancy overlay)
│   └── *.jpg                             # calibration reference stills (grid/line overlays)
└── docs/
    ├── EXPERIMENTS.md
    ├── SYSTEM_SPECIFICATION.md
    ├── PAPER_FACTS.md
    └── PAPER_TODO.md
```

> **Note on `vcamtesting2`:** results exist for a `vcamtesting2_bytetrack`
> experiment (events, timeline, annotated video, and a frozen config copy
> in `results/raw/`), but **no corresponding source config file is tracked
> in `config/`.** The experiment cannot currently be re-run from the
> `config/` directory as documented — see `docs/PAPER_TODO.md`.

Every module owns exactly one job: `detection.py` never tracks,
`tracking.py` never knows how detections were produced, `line_crossing.py`
never validates (it reports every raw candidate), `occupancy.py` has no
computer-vision code, and `main.py` only wires the others together. A
future validation stage would slot in between `line_crossing.py` and
`occupancy.py` without touching anything above it.

## Methodology

- **Detection:** Ultralytics YOLO (`yolo11n.pt`), called via `model.predict()`
  per frame — the built-in `model.track()` is deliberately not used, so
  detection and tracking stay independently swappable. Filtered by
  confidence threshold, IoU threshold, target class list (COCO class 0 =
  person by default), and inference image size, all from config.
- **Tracking:** Two interchangeable backends from the standalone `trackers`
  (Roboflow) package — `ByteTrackTracker` (Zhang et al.'s ByteTrack) and
  `BoTSORTTracker` (Aharon et al.'s BoT-SORT). Selected by `tracker.type`
  in config; no source change needed to switch. BoT-SORT optionally uses
  Camera Motion Compensation, which needs the raw frame — `tracking.py`
  hides this difference behind one `update()` call. A `tracker_id` of `-1`
  means the track is not yet confirmed; `line_crossing.py` filters these
  out before they can affect crossing state.
- **Line definition:** Two endpoints `(x1,y1)-(x2,y2)` in normalized
  coordinates (0.0–1.0 of frame width/height), so one config works across
  resolutions. Can be horizontal, vertical, or diagonal depending on the
  two points chosen. `in_is_downward` is a semantic label only — it
  selects which of Supervision's two raw crossing signals is reported as
  "IN" vs "OUT"; the correct value must be verified empirically per camera
  setup by checking the annotated video and events CSV.
- **Crossing logic:** Wraps `supervision.LineZone` with a `BOTTOM_CENTER`
  triggering anchor. No confidence filtering beyond the detector's own
  threshold, no minimum track age, and no protection against a track
  crossing back and forth (each crossing is reported independently) — this
  is by design for the frozen baseline.
- **Occupancy update:** `OccupancyEngine` increments on IN, decrements on
  OUT, and optionally clamps at a minimum of zero (`clamp_minimum_zero` in
  config). It tracks running totals of entries/exits and the maximum
  occupancy observed.
- **Logging:** `EventLogger` writes one row per accepted crossing to
  `<experiment_id>_events.csv` and one row per processed frame to
  `<experiment_id>_occupancy_timeline.csv`. Existing files for an
  `experiment_id` are never overwritten — a rerun gets a numeric suffix
  (`_1`, `_2`, ...).
- **Evaluation:** `evaluation.py` matches predicted vs. ground-truth
  entry/exit events within a configurable frame tolerance (default 15
  frames) and reports precision/recall/F1 per direction, plus occupancy
  MAE and max error against a ground-truth occupancy series (dense or
  inferred from sparse event rows). It computes only what it has real
  data for — missing ground truth is reported as a note, never guessed.
  **No experiment in this repository currently has a populated
  ground-truth CSV**, so no evaluation run has actually been executed —
  only the template exists at `data/ground_truth/ground_truth_template.csv`.

## Configuration

Every run is driven entirely by one YAML file (`config_loader.py` is the
single place that reads it — nothing is hard-coded). Top-level sections:
`experiment` (id, description), `video` (source path, whether to save an
annotated video, frame subsampling), `detection` (model weights, device,
confidence/IoU thresholds, target classes, inference size), `tracker`
(active type plus both `bytetrack` and `botsort` parameter blocks — only
the active one is used), `line` (two normalized endpoints + the
`in_is_downward` direction flag), `occupancy` (initial value, zero-clamp
flag), and `logging` (output directory). `frame_rate` for the tracker is
taken from the actual input video at runtime, not set in config.

## Calibration

The line is calibrated per camera setup by picking two pixel points that
form a line roughly perpendicular to the direction people walk through the
frame, then normalizing: `x_normalized = pixel_x / frame_width`,
`y_normalized = pixel_y / frame_height`. The tracked config files document
two different calibration approaches actually used:

- `v001_botsort_config.yaml` / `v001_calibration_config.yaml`: a
  **vertical** line at `x = 0.7218`, derived from a ceiling light
  fixture's tip pixel position (`345 / 478 px`), spanning the full frame
  height — for `test_v001.mp4` (478×850, portrait).
- `vcamtesting_bytetrack_config.yaml`: a **horizontal** line at
  `y = 0.7992` between `x = 0.1792` and `x = 0.6792` — for
  `vcamtesting.mp4` (848×478, landscape). Note: this file's header comment
  and `description` field are copy-pasted from the V001 vertical-line
  template and inaccurately describe this as "a vertical line at
  x=0.7218" — see `docs/PAPER_TODO.md`, this is a documentation bug, the
  actual line coordinates used are correct and as stated above.

`results/*.jpg` (`vcamtesting_grid.jpg`, `vcamtesting_line2.jpg`,
`vcamtesting_new_line.jpg`, `vcamtesting2_line3.jpg`) are calibration
reference stills — grid/line overlays used during this process.

## Trackers

`tracker.type` in config selects `"bytetrack"` or `"botsort"` — both
blocks stay present in every config file for comparison, only the active
one is applied (`config_loader.py: TrackerConfig.active_params()`).
Confirmed by the two `v001_*` experiments, which run the identical video
and line through both trackers.

## Running the System

Verified against the actual repository (config loading tested directly;
full inference was not re-executed in this audit — see
`docs/PAPER_TODO.md`). Always run from inside `src/`:

```powershell
cd src
python main.py --config ../config/v001_calibration_config.yaml
```

Run the same video/line through BoT-SORT instead, no code change:

```powershell
python main.py --config ../config/v001_botsort_config.yaml
```

Run the generic ByteTrack template on your own video (after editing
`video.source` and the `line` section for your camera):

```powershell
python main.py --config ../config/baseline_config.yaml
```

Override the experiment ID from the command line (useful for batch runs):

```powershell
python main.py --config ../config/baseline_config.yaml --experiment_id my_run_1
```

### Evaluation (not yet exercised in this repo)

Only meaningful once a populated ground-truth CSV exists (see
`data/ground_truth/ground_truth_template.csv` for the format):

```powershell
python evaluation.py --experiment_id v001_calibration ^
  --events_csv ../results/logs/v001_calibration_events.csv ^
  --timeline_csv ../results/logs/v001_calibration_occupancy_timeline.csv ^
  --ground_truth_csv ../data/ground_truth/<your_ground_truth>.csv ^
  --initial_occupancy 0 ^
  --output_csv ../results/logs/v001_calibration_evaluation.csv
```

(`^` is the PowerShell/CMD line-continuation character; the same command
works on one line without it.)

## Experiments

See `docs/EXPERIMENTS.md` for the full table. Four experiments have logged
results in this repository: `v001_calibration`, `v001_botsort`,
`vcamtesting_bytetrack`, `vcamtesting2_bytetrack`.

## Results

Real, verified numbers extracted directly from the tracked CSV files (not
re-derived or estimated):

| Experiment | Tracker | Video | Events | Final Occupancy | Max Occupancy |
|---|---|---|---|---|---|
| `v001_calibration` | ByteTrack | test_v001.mp4 | 1 IN (f119, conf 0.9166), 1 OUT (f624, conf 0.9212) | 0 | 1 |
| `v001_botsort` | BoT-SORT | test_v001.mp4 | 1 IN (f119, conf 0.9166), 1 OUT (f624, conf 0.9212) | 0 | 1 |
| `vcamtesting_bytetrack` | ByteTrack | vcamtesting.mp4 | Not consistent across reruns — see Limitations | Not consistent across reruns | 1 (in the first logged run) |
| `vcamtesting2_bytetrack` | ByteTrack | vcamtesting2.mp4 | 1 OUT (f101, conf 0.7952), clamped at 0 | 0 | 0 |

No accuracy, precision, recall, F1, MAE, RMSE, FPS, or latency figures are
reported here because no ground-truth CSV exists yet to compute them
against, and this audit did not re-run the pipeline to measure runtime
performance. `docs/PAPER_FACTS.md` and `docs/PAPER_TODO.md` mark exactly
what is verified versus still needed.

## Reproducibility

- Exact package versions are pinned in `requirements.txt`
  (`ultralytics==8.4.121`, `opencv-python-headless==4.13.0.92`,
  `supervision==0.30.0`, `trackers==2.6.0`, `torch==2.13.0`,
  `torchvision==0.28.0`, `PyYAML==6.0.3`) — all confirmed resolvable on
  PyPI as of this audit.
- Model weights: `yolo11n.pt`, Ultralytics' official pretrained release,
  auto-downloaded on first run if not already present in `models/`.
- Every executed run's exact config is copied to
  `results/raw/<experiment_id>_config_used.yaml`.
- **Important finding:** `v001_calibration` (3 reruns), `v001_botsort`,
  and `vcamtesting2_bytetrack` (2 reruns) are bit-for-bit reproducible
  across their logged reruns. `vcamtesting_bytetrack` is **not** — see
  Limitations below.
- Compiled bytecode in `src/__pycache__/` shows the pipeline has actually
  been executed under Python 3.12, 3.13, and 3.14, even though this is
  broader than any officially stated supported range in this repository
  (none was previously documented; do not assume 3.10–3.12 support
  without testing — see `docs/PAPER_TODO.md`).

## Limitations

- No confidence filtering beyond the detector's own threshold, no
  minimum track-age/persistence check, and no trajectory or direction
  validation before counting a crossing — a track crossing back and forth
  produces multiple raw events, by design.
- Camera-specific calibration is required per setup; the line and
  `in_is_downward` flag must be verified empirically for each new camera
  position.
- **Reproducibility gap (verified):** two logged runs of
  `vcamtesting_bytetrack_config.yaml` against the same video produced
  different outcomes. One run recorded a single IN event at frame 224
  (final occupancy 1); another run of the identical config recorded a
  single OUT event at frame 136 instead (final occupancy 0, clamped). The
  root cause has not been diagnosed as part of this audit — see
  `docs/PAPER_TODO.md`. This must be resolved or explained before any
  quantitative claim is made using this experiment.
- No ground-truth CSV currently exists for any experiment beyond an empty
  template, so no precision/recall/F1/MAE figures can yet be computed by
  `evaluation.py` for this repository.
- The `vcamtesting2_bytetrack` experiment has results but no tracked
  source config, so it cannot currently be reproduced from `config/` as
  documented.
- Comments inside `vcamtesting_bytetrack_config.yaml` and the frozen
  `results/raw/vcamtesting2_bytetrack_config_used.yaml` are copy-pasted
  from the V001 vertical-line template and inaccurately describe a
  vertical line at x=0.7218, when the actual `line:` values in both files
  define a different, horizontal line. The line values themselves (used
  to produce the logged results) are correct; only the prose comments are
  wrong.

## Future Work

Not implemented — potential directions only, to be proposed and evaluated
separately from this frozen baseline:

- Confidence-aware event validation
- Trajectory-based crossing validation
- Adaptive or multi-line crossing logic
- Improved occlusion handling
- Temporal/persistence-based event confirmation

## Citations

See `docs/PAPER_FACTS.md` for the technologies used (Ultralytics YOLO,
ByteTrack, BoT-SORT, Supervision) pending exact bibliographic confirmation
from the author before the paper is written.
