# Paper TODO

## MUST PROVIDE BEFORE PAPER WRITING

1. **Ground truth.** No populated ground-truth CSV exists for any
   experiment — only the empty template
   (`data/ground_truth/ground_truth_template.csv`). Every claim of a
   "matched" or "correct" result currently rests on comments inside config
   files, not on a file `evaluation.py` can actually check. Provide
   ground-truth CSVs (format documented in `src/evaluation.py`'s
   docstring and the template file) for at least the four experiments in
   `docs/EXPERIMENTS.md`, then run `evaluation.py` against each and commit
   the resulting evaluation CSVs.
2. **Diagnose the `vcamtesting_bytetrack` reproducibility failure.**
   Identical config, identical video, different results across reruns
   (IN at frame 224 in two runs vs. OUT at frame 136 in a third). This
   must be understood and either explained (e.g., a specific
   non-deterministic dependency) or resolved before this experiment's
   numbers can be used in the paper at all.
3. **Completed during repository finalization:** recovered
  `config/vcamtesting2_bytetrack_config.yaml` from the frozen snapshot in
  `results/raw/`. No result artifact was modified.
4. **Resolve the `V00` / `Test_v00.mp4` orphaned reference.** The
   previous README extensively documented a `V00` calibration experiment
   and a specific detection-failure finding (bounding box too wide due to
   close camera placement) that is not present anywhere in the current
   repository or Git history. Confirm whether this was: (a) superseded by
   `V001` and safe to drop, (b) accidentally omitted from version control
   and should be restored, or (c) from a different repository entirely.
5. **Hardware specification.** No CPU/GPU/RAM information is recorded
   anywhere. Needed for any FPS/latency claim and for the Experimental
   Setup section.
6. **Video provenance.** Number of subjects, recording setting, camera
   hardware, and whether these three videos are the final dataset or
   preliminary calibration clips.
7. **Author-confirmed Python version support range** (bytecode shows
   3.12–3.14 were actually used; no official range was previously
   documented).
8. **Authorship information** for the paper: authors, affiliations,
   target IEEE conference/venue and its format requirements.
9. **Completed for tracked source configs:** corrected stale line comments
  and removed unsupported ground-truth wording. The frozen raw snapshot in
  `results/raw/` was intentionally left unchanged because it is an
  experimental result artifact.

## OPTIONAL IMPROVEMENTS

- Re-run the full pipeline end-to-end in this environment (not done in
  this audit) to independently confirm `main.py` executes as documented
  with real GPU/CPU inference, rather than relying solely on static code
  reading plus config-loading validation.
- Add a `CITATIONS.md` with exact BibTeX for YOLO/Ultralytics, ByteTrack
  (Zhang et al.), BoT-SORT (Aharon et al.), and Supervision once the
  author confirms which paper versions/venues to cite.
- Consider whether `results/` (videos, annotated MP4s, CSVs) should stay
  tracked in Git at its current size (~23 MB annotated + ~9.7 MB raw
  video, ~102 MB total repo) versus documented as externally supplied —
  not changed in this audit since these are legitimate experimental
  artifacts and the instruction was not to remove such files without
  author sign-off.
- Decide on a repository name convention (`occupancy-estimation-baseline`
  vs. the previous README's `occupancy_estimation_baseline`) — cosmetic
  only.

## DO NOT CHANGE (frozen baseline)

- `src/detection.py` — YOLO detection wrapper and thresholds
- `src/tracking.py` — ByteTrack/BoT-SORT wrapper and selection logic
- `src/line_crossing.py` — line-crossing/crossing-acceptance logic
- `src/occupancy.py` — occupancy counting logic
- `src/evaluation.py` — evaluation formulas
- `src/main.py` — pipeline orchestration order
- All `line:`, `detection:`, and `tracker:` values inside every tracked
  config file (only their prose comments have documentation bugs — see
  item 9 above; the numeric values are correct and were not touched in
  this audit)
- All logged CSV/video results — not regenerated, not edited, not
  re-numbered

## Changes made in this audit (for the record)

- Removed `src/__pycache__/*.pyc` from Git tracking and added a proper
  `.gitignore` (no source or config files touched).
- Replaced `README.md` with a version reflecting only verified repository
  contents (previous version referenced a `V00` experiment/config/video
  that do not exist in this repository — flagged above, not silently
  resolved).
- Added `config/vcamtesting2_bytetrack_config.yaml` by recovering the
  run-defining values from its frozen result snapshot.
- Added `docs/EXPERIMENTS.md`, `docs/SYSTEM_SPECIFICATION.md`,
  `docs/PAPER_FACTS.md`, and this file.
- No file under `src/`, no `line:`/`detection:`/`tracker:` value in any
  config, and no file under `results/` or `data/` was modified.
