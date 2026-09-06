# Experiment Record

Authoritative record of every experiment with logged output in this
repository, extracted directly from tracked files under `results/` and
`config/`. Nothing here is estimated or inferred — where a value is not
present in the repository, it is marked `Not documented yet`.

## Experiment: `v001_calibration`

| Field | Value |
|---|---|
| Config | `config/v001_calibration_config.yaml` |
| Tracker | ByteTrack |
| Video | `data/videos/test_v001.mp4` (478×850, 30 fps, 719 frames, 23.93s — measured via ffprobe) |
| Line | Vertical, x = 0.7218 (derived from a ceiling-fixture tip at pixel x=345 of 478) |
| Initial occupancy | 0 |
| Predicted events | 1 IN (frame 119, t=3.96s, track_id=2, confidence=0.9166); 1 OUT (frame 624, t=20.767s, track_id=4, confidence=0.9212) |
| Final / max occupancy | 0 / 1 |
| Ground truth | No ground-truth CSV for this experiment is tracked in the repository; no ground-truth-validated result is reported here. |
| Reruns logged | Base + 3 reruns (`_1`, `_2`, `_3`) — all four bit-for-bit identical |
| Outputs | `results/logs/v001_calibration_events*.csv`, `results/logs/v001_calibration_occupancy_timeline*.csv`, `results/annotated/v001_calibration_annotated.mp4`, `results/raw/v001_calibration_config_used.yaml` |

## Experiment: `v001_botsort`

| Field | Value |
|---|---|
| Config | `config/v001_botsort_config.yaml` |
| Tracker | BoT-SORT (camera motion compensation enabled, `sparseOptFlow`) |
| Video | `data/videos/test_v001.mp4` (same file as above) |
| Line | Vertical, x = 0.7218 (identical to `v001_calibration`) |
| Initial occupancy | 0 |
| Predicted events | 1 IN (frame 119, t=3.96s, track_id=0, confidence=0.9166); 1 OUT (frame 624, t=20.767s, track_id=1, confidence=0.9212) |
| Final / max occupancy | 0 / 1 |
| Ground truth | Same as `v001_calibration` — claimed in config comments, not verifiable from a tracked ground-truth CSV. |
| Reruns logged | 1 (no numeric-suffix reruns present) |
| Outputs | `results/logs/v001_botsort_events.csv`, `results/logs/v001_botsort_occupancy_timeline.csv`, `results/annotated/v001_botsort_annotated.mp4`, `results/raw/v001_botsort_config_used.yaml` |
| Note | Frame/timestamp/confidence values are identical to `v001_calibration`; only `track_id` numbering differs between the two trackers on this clip. |

## Experiment: `vcamtesting_bytetrack`

| Field | Value |
|---|---|
| Config | `config/vcamtesting_bytetrack_config.yaml` |
| Tracker | ByteTrack |
| Video | `data/videos/vcamtesting.mp4` (848×478, 30 fps, 268 frames, 8.92s — measured via ffprobe) |
| Line | Horizontal, y = 0.7992, x from 0.1792 to 0.6792. **Note:** the config file's header comment and `description` field are copy-pasted from the V001 vertical-line template and incorrectly describe this as a vertical line at x=0.7218 — the `line:` values actually used (and shown here) are horizontal and were used to produce the results below. |
| Initial occupancy | 0 |
| Predicted events (base run) | 1 IN (frame 224, t=7.455s, track_id=3, confidence=0.9393) |
| Predicted events (rerun `_1`) | 1 IN (frame 224, t=7.455s, track_id=3, confidence=0.9393) — matches base |
| Predicted events (rerun `_2`) | 1 OUT (frame 136, t=4.526s, track_id=3, confidence=0.9276) — **does not match base or `_1`** |
| Final occupancy | 1 (base, `_1`) vs. 0 (rerun `_2`) — inconsistent across identical-config reruns |
| Ground truth | Not documented — no ground-truth CSV tracked for this experiment. |
| Reruns logged | Base + 2 reruns (`_1`, `_2`) |
| Outputs | `results/logs/vcamtesting_bytetrack_events*.csv`, `results/logs/vcamtesting_bytetrack_occupancy_timeline*.csv`, `results/annotated/vcamtesting_bytetrack_annotated.mp4`, `results/raw/vcamtesting_bytetrack_config_used.yaml` |
| **Flag** | **Verified reproducibility failure.** This is the only experiment in the repository where reruns of an identical config against an identical video diverge. Root cause not diagnosed in this audit — see `PAPER_TODO.md`. Do not treat any single run of this experiment as representative until resolved. |

## Experiment: `vcamtesting2_bytetrack`

| Field | Value |
|---|---|
| Config | `config/vcamtesting2_bytetrack_config.yaml` (recovered from the frozen snapshot at `results/raw/vcamtesting2_bytetrack_config_used.yaml`; result artifacts unchanged) |
| Tracker | ByteTrack (per frozen config) |
| Video | `data/videos/vcamtesting2.mp4` (478×850, 30 fps, 341 frames, 11.35s — measured via ffprobe) |
| Line | Per frozen config: x from 0.1792 to 0.6792 at y = 0.7992 (same coordinate values as `vcamtesting_bytetrack`, applied to a different, portrait-orientation video). Same stale-comment issue as `vcamtesting_bytetrack` — header text describes a vertical x=0.7218 line that is not what the tracked `line:` values define. |
| Initial occupancy | 0 |
| Predicted events (base, rerun `_1`, rerun `_2`) | 1 OUT (frame 101, t=3.361s, track_id=0, confidence=0.7952) — identical across all 3 logged runs |
| Final / max occupancy | 0 / 0 (the OUT event was clamped at zero since occupancy started at 0) |
| Ground truth | Not documented — no ground-truth CSV tracked for this experiment. |
| Reruns logged | Base + 2 reruns (`_1`, `_2`) — all three bit-for-bit identical |
| Outputs | `results/logs/vcamtesting2_bytetrack_events*.csv`, `results/logs/vcamtesting2_bytetrack_occupancy_timeline*.csv`, `results/annotated/vcamtesting2_bytetrack_annotated.mp4`, `results/raw/vcamtesting2_bytetrack_config_used.yaml` |
| **Flag** | The logged reruns are reproducible, but no ground-truth CSV is tracked. The source config is available under `config/`; the frozen raw snapshot remains part of the result record. |

## Configs present but never run

| Config | Why not run |
|---|---|
| `config/baseline_config.yaml` | Generic ByteTrack template; `video.source` points to a placeholder `../data/videos/your_video.mp4` that does not exist in the repository. |
| `config/botsort_config.yaml` | Generic BoT-SORT template; same placeholder video path, does not exist. |

## Orphaned references (not present in this repository)

The previous version of this README referenced a `V00` experiment
(`Test_v00.mp4`, `config/v00_calibration_config.yaml`) with a documented
0/0-detection failure mode caused by a too-close camera. **Neither the
video file nor the config file exists anywhere in this repository or its
Git history at the time of this audit.** This may reflect an earlier
project state, a since-removed file, or a renaming to `V001` — this cannot
be determined from the repository alone. See `PAPER_TODO.md`: this needs
author confirmation before either including or fully removing the V00
narrative from paper materials.
