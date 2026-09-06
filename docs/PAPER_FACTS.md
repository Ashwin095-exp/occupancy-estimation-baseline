# Paper Facts — Verified Foundation

Every line below is tagged with its source. Nothing here is invented.
Where a value is not available in the repository, it says so explicitly.

### Problem
- **Verified from code/README:** Estimating real-time occupancy of a
  monitored space from a single video feed, using virtual line-crossing
  counting.

### Objective
- **Verified from README/code comments:** Establish a frozen, conventional
  (unvalidated) line-crossing baseline first, to (a) prove the pipeline
  works end-to-end and (b) generate reference numbers for a future,
  not-yet-implemented validation method to be compared against.

### Input
- **Verified from code:** Single video file per run, read via OpenCV
  (`cv2.VideoCapture`). No live-camera input path implemented.

### Dataset / Videos
- **Verified from repository (`data/videos/`, confirmed via ffprobe):**
  - `test_v001.mp4` — 478×850 (portrait), 30 fps, 719 frames, 23.93s
  - `vcamtesting.mp4` — 848×478 (landscape), 30 fps, 268 frames, 8.92s
  - `vcamtesting2.mp4` — 478×850 (portrait), 30 fps, 341 frames, 11.35s
- **Needs confirmation from author:** number of distinct human subjects
  per video, recording conditions (lighting, camera hardware, mounting
  height/angle beyond what's inferable from calibration comments),
  whether these are the final dataset or preliminary calibration clips.

### Detector
- **Verified from code:** Ultralytics YOLO, called via `model.predict()`
  (detection only, no built-in tracking used).

### Detection Model
- **Verified from config/repository:** `yolo11n.pt`, official Ultralytics
  pretrained weights, auto-downloaded on first run if absent (5.4 MB file
  confirmed present in `models/`).

### Tracker
- **Verified from code:** Two interchangeable backends from the
  standalone `trackers` (Roboflow) package: `ByteTrackTracker` (based on
  Zhang et al.'s ByteTrack) and `BoTSORTTracker` (based on Aharon et al.'s
  BoT-SORT), selected per-run by config with no code change.

### Tracking Configuration
- **Verified from config files:** ByteTrack —
  `track_activation_threshold=0.25`, `lost_track_buffer=30`,
  `minimum_iou_threshold=0.8`, `minimum_consecutive_frames=2`. BoT-SORT —
  same activation/buffer/consecutive-frame values, plus
  `minimum_iou_threshold_first_assoc=0.2`,
  `minimum_iou_threshold_second_assoc=0.5`,
  `minimum_iou_threshold_unconfirmed_assoc=0.3`,
  `high_conf_det_threshold=0.6`, `enable_cmc=true`,
  `cmc_method="sparseOptFlow"`.

### Line-Crossing Method
- **Verified from code:** `supervision.LineZone` with a `BOTTOM_CENTER`
  triggering anchor. Line defined by two normalized-coordinate endpoints,
  supporting horizontal, vertical, or diagonal orientation. Unconfirmed
  tracks (`tracker_id == -1`) are filtered out before crossing evaluation.
  No confidence gating beyond detection threshold, no persistence check,
  no duplicate-crossing suppression.

### Occupancy Calculation
- **Verified from code:** Simple running counter — `+1` per IN event,
  `-1` per OUT event, optional clamp at a minimum of 0
  (`clamp_minimum_zero`, true in every tracked config).

### Initial Occupancy Handling
- **Verified from config files:** `initial_occupancy: 0` in every tracked
  config used to produce the logged results.

### Evaluation Method
- **Verified from code:** Greedy nearest-frame one-to-one matching of
  predicted vs. ground-truth entry/exit events within a configurable
  tolerance (default 15 frames); precision/recall/F1 per direction;
  occupancy MAE and max absolute error against a ground-truth occupancy
  series (dense values take precedence over sparse-event-inferred values).

### Metrics
- **Verified from code (implemented, not yet computed on real data):**
  entry/exit precision, recall, F1; occupancy MAE; occupancy max error.
- **Needs confirmation from author / not available in repository:** any
  actual computed value for the above — no ground-truth CSV exists yet
  beyond the empty template.

### Hardware
- **Not available in repository — author confirmation required.** Config
  files set `device: "cpu"` for every logged run; no CPU model, RAM, or
  GPU information is recorded anywhere in the repository.

### Software
- **Verified from `requirements.txt`, confirmed installable on PyPI as of
  this audit:** `ultralytics==8.4.121`, `opencv-python-headless==4.13.0.92`,
  `supervision==0.30.0`, `trackers==2.6.0`, `torch==2.13.0`,
  `torchvision==0.28.0`, `PyYAML==6.0.3`.

### Python Version
- **Not officially documented in the (previous) README.** Compiled
  bytecode present in the repository (`src/__pycache__/`, before this
  audit's cleanup) shows execution under Python 3.12, 3.13, and 3.14.
  **Needs confirmation from author:** which version(s) should be stated as
  officially supported for the paper/reproducibility section.

### Dependencies
- See Software, above. Full list is exactly the seven pinned packages in
  `requirements.txt` — no other runtime dependencies are declared.

### Experiments
- **Verified from repository:** 4 experiments with logged results
  (`v001_calibration`, `v001_botsort`, `vcamtesting_bytetrack`,
  `vcamtesting2_bytetrack`) — full detail in `docs/EXPERIMENTS.md`. 2
  additional generic template configs exist but were never run.

### Results
- **Verified from tracked CSVs (see docs/EXPERIMENTS.md for full detail):**
  - `v001_calibration` / `v001_botsort`: identical result on both
    trackers — 1 IN (frame 119, conf 0.9166), 1 OUT (frame 624, conf
    0.9212), final occupancy 0, max 1. Reproducible across all logged
    reruns.
  - `vcamtesting2_bytetrack`: 1 OUT (frame 101, conf 0.7952), clamped to
    occupancy 0. Reproducible across all logged reruns.
  - `vcamtesting_bytetrack`: **not reproducible** — reruns of the
    identical config/video produced different events (IN at frame 224 in
    two runs vs. OUT at frame 136 in a third run).
- **Needs confirmation from author / not available in repository:** any
  ground-truth-validated accuracy figure for any experiment. No populated
  ground-truth CSV backing such a claim is tracked in this repository.

### Limitations
- See README "Limitations" and `docs/EXPERIMENTS.md` per-experiment flags
  — primarily: no validated ground truth yet and one experiment's
  non-reproducibility. The `vcamtesting2` source config was recovered from
  its frozen result snapshot during repository finalization; logged outputs
  were not changed.

### Reproducibility
- Every executed run's exact config is frozen to `results/raw/`. Package
  versions are pinned and confirmed installable. Model weights are a
  known, official, reproducible download. Three of four experiments are
  bit-for-bit reproducible across logged reruns; one is not (see above).

### Known Missing Information
- See `docs/PAPER_TODO.md` for the consolidated, actionable checklist.
