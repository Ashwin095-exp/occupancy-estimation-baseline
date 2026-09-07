# Reproducibility Guide

This document provides the foundation for reproducing the baseline system and verified experiments documented in this repository.

## Environment & Dependencies

All package versions are pinned in `requirements.txt`:

```
ultralytics==8.4.121
opencv-python-headless==4.13.0.92
supervision==0.30.0
trackers==2.6.0
torch==2.13.0
torchvision==0.28.0
PyYAML==6.0.3
```

These versions are confirmed resolvable on PyPI and were used to generate all tracked experimental results. Installation:

```bash
pip install -r requirements.txt
```

**Python version:** Bytecode evidence shows successful execution under Python 3.12, 3.13, and 3.14. No minimum or maximum version is formally specified; test in your target Python version.

## Model Weights

- **Detection:** `yolo11n.pt` — Ultralytics' official YOLO11 Nano pretrained weights
  - Automatically downloaded to `models/yolo11n.pt` on first run if absent
  - ~5.4 MB, reproducible download from Ultralytics mirrors
  - Used in every experiment via `detection.model_weights` config parameter

## Hardware

All tracked experiments used `device: "cpu"` in their configs. No GPU information is recorded. For FPS/latency measurement or reproducing with GPU acceleration:

1. Specify `device: "cuda"` or `device: "0"` in the config
2. Ensure `torch` and `torchvision` versions match your CUDA toolkit
3. Document actual hardware (CPU model, GPU model/VRAM, RAM) for the paper's Experimental Setup section

## Reproduction Commands

All experiments are run from inside the `src/` directory:

```bash
cd src
python main.py --config ../config/<config_name>.yaml
```

### Verified Reproducible Experiments

#### A. v001_calibration (ByteTrack)

```bash
python main.py --config ../config/v001_calibration_config.yaml
```

**Expected:** 1 IN event (frame 119, confidence 0.9166) and 1 OUT event (frame 624, confidence 0.9212); final occupancy 0, max occupancy 1. Identical across all logged reruns.

#### B. v001_botsort (BoT-SORT)

```bash
python main.py --config ../config/v001_botsort_config.yaml
```

**Expected:** Same events as v001_calibration (same video and line); only tracker type differs. Final occupancy 0, max occupancy 1.

#### C. vcamtesting_bytetrack (ByteTrack)

```bash
python main.py --config ../config/vcamtesting_bytetrack_config.yaml
```

**Expected:** This experiment has a documented reproducibility issue (see "Known Issues" below). The base and first rerun show 1 IN event at frame 224 (final occupancy 1). A third rerun shows 1 OUT event at frame 136 (final occupancy 0). Root cause not yet diagnosed.

## Output Files

Every run produces three types of output under `results/`:

1. **Events CSV** — `results/logs/<experiment_id>_events.csv`
   - Columns: frame, timestamp_sec, track_id, detection_confidence, crossing_direction, predicted_event, occupancy_after_event
   - One row per crossing event detected

2. **Occupancy timeline CSV** — `results/logs/<experiment_id>_occupancy_timeline.csv`
   - Columns: frame, timestamp_sec, occupancy, max_occupancy_so_far
   - One row per processed frame

3. **Frozen config snapshot** — `results/raw/<experiment_id>_config_used.yaml`
   - Exact YAML used to produce this run's results
   - Enables post-hoc verification of parameter values

4. **Annotated video** (if `video.save_annotated_video: true`) — `results/annotated/<experiment_id>_annotated.mp4`
   - Boxes, track IDs, line overlay, and live occupancy counter

## Evaluation (Not Yet Exercised)

The pipeline includes an optional `evaluation.py` for comparing predicted events/occupancy against ground-truth data:

```bash
python evaluation.py \
  --experiment_id v001_calibration \
  --events_csv ../results/logs/v001_calibration_events.csv \
  --timeline_csv ../results/logs/v001_calibration_occupancy_timeline.csv \
  --ground_truth_csv ../data/ground_truth/my_ground_truth.csv \
  --initial_occupancy 0 \
  --output_csv ../results/logs/v001_calibration_evaluation.csv
```

**Note:** No populated ground-truth CSV exists in this repository yet. The template format is documented in `src/evaluation.py` and a format-only example is at `data/ground_truth/ground_truth_template.csv`.

## Known Issues & Limitations

### Reproducibility Issue: vcamtesting_bytetrack

Multiple reruns of the same config and video produced different events:
- Runs 0 and 1: 1 IN event at frame 224 (final occupancy 1)
- Run 2: 1 OUT event at frame 136 (final occupancy 0)

**Root cause:** Not yet diagnosed as part of this audit.

**Impact:** Until this is resolved, quantitative claims using `vcamtesting_bytetrack` results must include a reproducibility caveat.

**Investigation needed:**
- Determinism in YOLO detection across reruns (identical seed, device, inference parameters)
- ByteTrack tracker state initialization and non-deterministic tie-breaking
- Frame-to-frame non-determinism in any dependency (OpenCV, NumPy)

### Detection & Tracking Assumptions

1. No confidence filtering beyond the detector's own threshold
2. No minimum track age or persistence requirement before a crossing is accepted
3. No trajectory or direction validation — a track crossing back and forth produces multiple raw events
4. Unconfirmed tracks (`tracker_id == -1`) are dropped before crossing evaluation (tracking hygiene)
5. Camera-specific line calibration required per setup

### Ground Truth Not Available

No ground-truth CSV exists for any experiment. Evaluation metrics (precision, recall, F1, MAE) cannot be computed.

### Methodological Limitations

- **No validation method:** The baseline is intentionally unvalidated. A future validation stage (confidence gating, persistence checks, trajectory analysis) would be inserted between line-crossing detection and occupancy updating.
- **Single camera:** No multi-camera coordination or transition handling.
- **No occlusion handling:** Overlapping detections may be double-counted if both cross the line.

## Videos & Calibration

### Video Specifications

| Video | Resolution | FPS | Duration | Frames | Use |
|---|---|---|---|---|---|
| test_v001.mp4 | 478×850 (portrait) | 30 | 23.93s | 719 | v001_calibration, v001_botsort experiments |
| vcamtesting.mp4 | 848×478 (landscape) | 30 | 8.92s | 268 | vcamtesting_bytetrack experiment |

**Calibration artifacts:** Reference stills with grid/line overlays are in `results/*.jpg` for manual verification of line placement.

### Line Calibration Method

1. Identify pixel coordinates of two points forming a line roughly perpendicular to human movement
2. Normalize: `x_norm = pixel_x / frame_width`, `y_norm = pixel_y / frame_height`
3. Set `in_is_downward` by visual inspection of the annotated video to confirm correct event direction

**Examples from tracked experiments:**
- v001: Vertical line at x=0.7218 (pixel x=345 of 478 width, derived from ceiling fixture)
- vcamtesting: Horizontal line at y=0.7992 from x=0.1792 to x=0.6792

## Final Experiment Set

Only these three experiments are documented as reproducible baselines for the paper:

1. **v001_calibration** — ByteTrack, test_v001.mp4, vertical line, reproducible
2. **v001_botsort** — BoT-SORT, test_v001.mp4, vertical line, reproducible
3. **vcamtesting_bytetrack** — ByteTrack, vcamtesting.mp4, horizontal line, **reproducibility issue documented** (see "Known Issues")

A fourth experiment (`vcamtesting2_bytetrack`) exists in the repository with reproducible results, but is retained as historical record only and is not part of the final paper's validated experiment set.

## Claims That Cannot Be Made From Current Repository

- Quantitative accuracy (no ground truth)
- Precision/recall/F1 for event detection (no ground truth)
- Occupancy MAE or max error (no ground truth)
- FPS or latency (not measured in tracked results)
- Hardware requirements or performance vs. alternatives
- Novelty beyond a conventional line-crossing baseline

See `docs/PAPER_FACTS.md` for the authoritative list of verified vs. unverified claims.

## For Paper Writing

Use these sections to populate the corresponding paper sections:

- **System Architecture / Methodology:** `docs/SYSTEM_SPECIFICATION.md`
- **Experimental Configuration & Results:** `docs/EXPERIMENTS.md`
- **Verified Facts & Technology References:** `docs/PAPER_FACTS.md`
- **Reproducibility / Supplementary Material:** This file

## Troubleshooting

**Config not found:** Ensure you are in the `src/` directory. Config paths are relative to there.

**Model download fails:** Check internet connection and PyPI/Ultralytics mirror availability. Pre-download `yolo11n.pt` and place it in `models/` if needed.

**Video not found:** Check that `data/videos/` contains the expected MP4 files.

**Different results on rerun:** Known issue for `vcamtesting_bytetrack` (documented above). For other experiments, check that config file has not been modified and dependencies have not changed.

