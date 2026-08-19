# Occupancy Estimation — Frozen Baseline

Conventional line-crossing occupancy counter: pretrained YOLO detection →
ByteTrack **or** BoT-SORT tracking (config-selectable) → unvalidated line
crossing → occupancy counting → CSV logging → optional evaluation against
ground truth.

**This is the frozen baseline.** No confidence-aware validation, trajectory
analysis, or any other research method is implemented yet — this exists to
(a) prove the pipeline works end-to-end, and (b) generate the reference
numbers a future proposed method would be compared against.

---

## 1. Project structure

```
occupancy_estimation_baseline/
├── README.md
├── requirements.txt
├── config/
│   ├── baseline_config.yaml           # default template, ByteTrack, generic line — calibrate before use
│   ├── botsort_config.yaml            # same as above, BoT-SORT selected
│   └── v00_calibration_config.yaml    # worked example: vertical line at LED-tip x-coordinate
├── models/
│   └── yolo11n.pt                      # YOLO weights — auto-downloaded on first run if absent
├── src/
│   ├── config_loader.py                # loads + validates + freezes config per run
│   ├── detection.py                    # YOLO wrapper — detection ONLY, no tracking
│   ├── tracking.py                     # ByteTrack / BoT-SORT wrapper, selected by config
│   ├── line_crossing.py                # conventional, unvalidated line-crossing logic
│   ├── occupancy.py                    # pure counting engine, no CV code at all
│   ├── event_logger.py                 # CSV logging, never overwrites prior runs
│   ├── evaluation.py                   # compares pipeline output to ground truth (optional)
│   └── main.py                         # orchestrator — wires modules together, no logic of its own
├── data/
│   ├── videos/                         # PUT YOUR INPUT VIDEOS HERE
│   └── ground_truth/
│       └── ground_truth_template.csv   # format reference for evaluation.py
└── results/
    ├── raw/                            # frozen config copy for every run
    ├── logs/                           # events + occupancy timeline CSVs
    └── annotated/                      # QA video with boxes/IDs/line/occupancy overlay
```

Every module only knows about its own job — `detection.py` never tracks,
`tracking.py` never knows how detections were produced, `line_crossing.py`
never validates (it reports every raw crossing candidate), `occupancy.py`
has no computer-vision code at all, and `main.py` contains no logic of its
own, only orchestration. A future confidence-aware method would slot in as
a new module between `line_crossing.py` and `occupancy.py` without
modifying any of the files above it.

---

## 2. Windows setup instructions

### 2.1 Prerequisites

- **Python 3.10, 3.11, or 3.12** (64-bit). Download from
  [python.org](https://www.python.org/downloads/windows/) if you don't have
  it. During install, check **"Add python.exe to PATH"**.
- Internet access for the initial setup (package install + one-time YOLO
  weights download, ~5.6 MB).

### 2.2 Get the project onto your machine

Copy the entire `occupancy_estimation_baseline/` folder to your laptop,
e.g. to `C:\Users\<you>\occupancy_estimation_baseline\`.

### 2.3 Open a terminal in the project folder

Open **PowerShell** (or Command Prompt) and navigate to the project:

```powershell
cd C:\Users\<you>\occupancy_estimation_baseline
```

### 2.4 Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

Your prompt should now show `(venv)` at the start of the line. If
PowerShell blocks the activation script with an execution-policy error, run
this once (as your normal user, not admin) and try activating again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2.5 Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Ultralytics (YOLO), OpenCV, Supervision, the `trackers`
package (ByteTrack + BoT-SORT), PyTorch (CPU build — see note below), and
PyYAML. It will take a few minutes; PyTorch is the largest download.

> **GPU note:** the pinned `torch`/`torchvision` versions above install a
> standard PyPI build. If you have an NVIDIA GPU and want CUDA
> acceleration, install a CUDA-enabled PyTorch build for your GPU/driver
> from [pytorch.org](https://pytorch.org/get-started/locally/) *before*
> running `pip install -r requirements.txt` (pip will not downgrade an
> already-satisfied torch requirement), then set `device: "cuda:0"` in
> your config. CPU works fine for testing at the frame rates in this
> project; it's just slower than a GPU would be.

### 2.6 First run will download YOLO weights automatically

The first time you run the pipeline, Ultralytics will download
`yolo11n.pt` (~5.6 MB) from its official GitHub release into `models/` if
it isn't already there. This needs internet access once; after that it's
cached locally and reused.

---

## 3. Input video folder structure

Place your video files in `data/videos/`:

```
data/videos/
├── Test_v00.mp4
├── (other recordings you make later)
```

Reference them in a config's `video.source` field as a path relative to
`src/` (since that's where you run `main.py` from), e.g.:

```yaml
video:
  source: "../data/videos/Test_v00.mp4"
```

---

## 4. Exact commands to run a video through the pipeline

Always run from inside the `src/` folder:

```powershell
cd src
python main.py --config ../config/v00_calibration_config.yaml
```

To run the generic default config (ByteTrack) on your own video, after
editing `config/baseline_config.yaml`'s `video.source` and `line` section
for your camera setup:

```powershell
python main.py --config ../config/baseline_config.yaml
```

To run the same video through BoT-SORT instead (for tracker comparison),
with no code changes — just point at the BoT-SORT config:

```powershell
python main.py --config ../config/botsort_config.yaml
```

Optionally override the experiment ID from the command line (useful when
batch-running the same config against multiple videos):

```powershell
python main.py --config ../config/baseline_config.yaml --experiment_id my_run_1
```

### Running evaluation against ground truth (optional)

Only meaningful once you have a hand-labeled ground-truth CSV (see
`data/ground_truth/ground_truth_template.csv` for the format):

```powershell
python evaluation.py --experiment_id v00_calibration ^
  --events_csv ../results/logs/v00_calibration_events.csv ^
  --timeline_csv ../results/logs/v00_calibration_occupancy_timeline.csv ^
  --ground_truth_csv ../data/ground_truth/v00_ground_truth.csv ^
  --initial_occupancy 0 ^
  --output_csv ../results/logs/v00_calibration_evaluation.csv
```

(The `^` line-continuation character is PowerShell/CMD syntax; on one line
it's the same command without the `^` characters and line breaks.)

---

## 5. Output folder structure

After a run, you'll find:

```
results/
├── raw/
│   └── <experiment_id>_config_used.yaml       # exact config that produced this run — traceability
├── logs/
│   ├── <experiment_id>_events.csv              # one row per accepted crossing event
│   ├── <experiment_id>_occupancy_timeline.csv  # one row per processed frame
│   └── <experiment_id>_evaluation.csv          # only if you ran evaluation.py
└── annotated/
    └── <experiment_id>_annotated.mp4           # visual QA video (boxes, IDs, line, occupancy overlay)
```

Existing result files for the same `experiment_id` are **never
overwritten** — a rerun gets a numeric suffix (`_1`, `_2`, ...) instead.

### `events.csv` columns

| column | meaning |
|---|---|
| `frame` | frame index (0-based) the event was logged on |
| `timestamp_sec` | frame index / video FPS |
| `track_id` | the confirmed tracker ID that crossed the line |
| `detection_confidence` | YOLO confidence for that detection at the crossing frame |
| `crossing_direction` | `IN` or `OUT` |
| `predicted_event` | same as `crossing_direction` (kept as a separate column for downstream compatibility with experiment logs) |
| `occupancy_after_event` | running occupancy immediately after this event was applied |

### `occupancy_timeline.csv` columns

| column | meaning |
|---|---|
| `frame` | frame index |
| `timestamp_sec` | frame index / video FPS |
| `occupancy` | current occupancy at this frame |
| `max_occupancy_so_far` | running maximum occupancy up to this frame |

---

## 6. How the virtual counting line is defined

The line is defined in config by two endpoints, `(x1,y1)` and `(x2,y2)`,
in **normalized coordinates** (0.0–1.0 relative to frame width/height), so
the same config works regardless of video resolution:

```yaml
line:
  x1: 0.8222
  y1: 0.0
  x2: 0.8222
  y2: 1.0
  in_is_downward: true
```

Because it's just two points, the line can be:

- **Horizontal** (`y1 == y2`) — appropriate when people move mostly
  *vertically* through the frame (e.g. an overhead camera looking down a
  hallway).
- **Vertical** (`x1 == x2`) — appropriate when people move mostly
  *horizontally* through the frame (e.g. a side-on camera watching someone
  walk left-to-right past a doorway). **This is the case used for
  V00** — see section 7 below.
- **Diagonal** — any other combination of endpoints.

To calibrate for your own camera: pick two pixel points that form a line
roughly perpendicular to the direction people actually walk through your
frame, then convert to normalized coordinates:

```
x_normalized = pixel_x / frame_width
y_normalized = pixel_y / frame_height
```

`in_is_downward` is a **semantic label, not a geometric constraint** — it
only controls which of the two raw crossing signals gets reported as `IN`
vs `OUT`. Its correct value depends on your specific camera setup and
should be verified empirically: run once, check the annotated video and
the events CSV against what you know actually happened, and flip the
boolean if IN/OUT come out reversed.

---

## 7. V00 calibration: the LED-tip line, explained

`config/v00_calibration_config.yaml` is a **worked, documented example** of
line calibration for the `Test_v00.mp4` recording.

**How the line was derived:** `Test_v00.mp4` is 478×850 (portrait). A
ceiling-mounted light fixture ("LED") is visible near the top of the
frame. Its tip (near end, closest to the camera) was located precisely by
cropping the frame around the fixture and overlaying a pixel grid, giving
tip pixel coordinates **x = 393px**. Normalized: `393 / 478 = 0.8222`.

Per the calibration instruction, the counting line is the **vertical
projection of that x-coordinate down to the ground** — i.e. a vertical
line at `x_normalized = 0.8222`, spanning the full frame height
(`y1=0.0, y2=1.0`). The LED itself is **not** used as the line (it is not
a horizontal line at the LED's height), and the line is **not diagonal**.

### Known limitation found during calibration — read before recording more data

Running the frozen, unmodified baseline against `Test_v00.mp4` with this
correctly-placed vertical line currently produces **0 detected IN / 0
detected OUT**, not the expected 1/1. This was verified by direct testing,
not assumed — the result is reported honestly here rather than tuned away.

**Root cause: camera distance, not line placement.** The person's
detection bounding box occupies roughly **35–100% of the frame width**
during the walk (the camera is positioned close to the subject). When a
single bounding box is that wide, it straddles any vertical line placed
within the frame for many consecutive frames, instead of cleanly
transitioning from "left of line" to "right of line" in one frame — which
is what standard line-crossing logic (Supervision's `LineZone`, used here)
expects. This is compounded by a second, independent finding: the tracker
loses and re-acquires the person's ID repeatedly during fast, close-range
motion (up to 9 distinct IDs were observed across just two passes in this
clip), so even a geometrically perfect line rarely sees one continuous
track ID crossing it.

**What this means for recording the rest of your dataset:** position the
camera further from the subject so a person's bounding box is a modest
fraction of frame width (a reasonable target: under ~25–30%). This is
standard practice for line-crossing counting cameras generally, not
specific to this codebase.

**What was deliberately NOT done:** the algorithm, thresholds, and line
placement were not adjusted to force a 1/1 result on this clip. Per
instruction, this is the frozen baseline — V00 is a calibration/diagnostic
video, not a tuning target.

---

## 8. Verification checklist — what a successful run should look like

Use this checklist once you record a video with adequate camera distance
(see section 7). It describes what a **correctly functioning** run looks
like — it is a target for well-framed footage, not a claim about the
current `Test_v00.mp4` result (see section 7's limitation).

For a clip where one person walks into frame, crosses the line once, and
walks back out (crossing it once more), a healthy run should show:

- [ ] **Console summary** reports `Total entries: 1` and `Total exits: 1`
- [ ] **`events.csv`** has exactly two rows: one `IN`, one `OUT`, in
      chronological order, at frame numbers matching when the person
      visually crosses the line in the annotated video
- [ ] **Both rows share the same `track_id`** if the person never left and
      re-entered frame between the two crossings — a different `track_id`
      on the OUT row is only expected if the person left the frame
      entirely between passes (as in V00, where they exit-frame between
      the two crossings)
- [ ] **`detection_confidence`** on both rows is reasonably high (as a
      rough guide, above ~0.5) — very low confidence at the exact crossing
      frame is worth a visual check
- [ ] **`occupancy_timeline.csv`** shows the value **0 → 1 → 0**: starts
      at the configured `initial_occupancy` (0), steps up to 1 at the IN
      event's frame, stays at 1 until the OUT event's frame, then returns
      to 0 and stays there
- [ ] **Annotated video**: the bounding box tracks the person continuously
      with a stable ID label (not flickering between `unconfirmed` and
      multiple different ID numbers), the line renders at the intended
      position, and the on-screen `in:`/`out:` counters and `Occupancy:`
      overlay match the CSV values at the corresponding timestamps
- [ ] **Bounding box width** stays a modest fraction of total frame width
      throughout (visual check on the annotated video) — if it's
      regularly over ~40–50% of frame width, back the camera up before
      recording further videos

If any of these don't hold, don't proceed to record the rest of the
dataset — fix the camera setup or line placement first and re-run this
checklist on a new short test clip.

---

## 9. What this baseline deliberately does NOT do

- No confidence filtering beyond the YOLO detection threshold.
- No minimum track-age / persistence check before counting a crossing.
- No trajectory or direction consistency validation.
- No duplicate-event protection — a track crossing back and forth will
  generate multiple raw events, by design (this is the known weakness a
  future proposed method is meant to address).

## 10. Other known limitations

- `sv.ByteTrack` is deprecated as of `supervision==0.28.0`; this project
  uses the replacement `ByteTrackTracker` (and `BoTSORTTracker`) from the
  standalone `trackers` package instead — no deprecation warnings should
  appear during normal use.
- Tracker ID fragmentation under fast/close motion (see section 7) is a
  general limitation of the frozen baseline, not specific to V00 — expect
  it on any footage with similar camera-to-subject distance.
- `evaluation.py` only computes metrics it has real ground-truth data for;
  it reports missing metrics with an explanatory note rather than
  estimating them.

## 11. Reproducibility

- Exact package versions are pinned in `requirements.txt` — freeze these
  before running final experiments; don't update mid-study.
- Exact model weights file is recorded in each config (`yolo11n.pt`,
  official Ultralytics GitHub release).
- Every run's config is copied into `results/raw/` — results can always be
  traced back to the parameters that produced them.
