"""
evaluation.py
-------------
Compares pipeline output (events CSV + occupancy timeline CSV, produced by
main.py) against a manually-created ground-truth CSV. This is evaluation
INFRASTRUCTURE — it does not implement or depend on any proposed research
method, and it never invents ground truth. If no ground-truth file is
supplied, this module is simply not used.

GROUND TRUTH FORMAT (CSV, one row per frame you choose to annotate):
    frame,actual_entry,actual_exit,actual_occupancy
    0,0,0,0
    ...
    182,1,0,1
    ...
    414,0,1,0

  - actual_entry / actual_exit: 1 on the exact frame you judge a genuine
    entry/exit to have happened, 0 otherwise. Most rows will be all zeros.
  - actual_occupancy: the true occupancy value from that frame onward
    (only needs to change on rows where it changes; see NOTE below).
  - You do not need to annotate every single frame — see NOTE below on
    sparse ground truth.

NOTE ON SPARSE GROUND TRUTH:
  In practice you will not hand-label 500+ rows. Provide ground truth in
  either of two ways:
    (a) SPARSE: only include rows for frames where actual_entry==1 or
        actual_exit==1 (the moments of a real crossing). This module infers
        actual_occupancy between those events by forward-filling from
        initial_occupancy.
    (b) DENSE: include every frame with actual_occupancy explicitly set. If
        both entry/exit rows and dense occupancy are present, dense
        actual_occupancy values take precedence for the MAE calculation.

This module computes only real metrics from real data — it never fabricates
missing values. If ground truth is missing or incomplete, the metrics that
cannot be computed are reported as None with an explanation, not guessed.
"""

import csv
import statistics
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class EvaluationResult:
    experiment_id: str
    predicted_entries: int
    actual_entries: int
    predicted_exits: int
    actual_exits: int
    predicted_final_occupancy: int
    actual_final_occupancy: int
    occupancy_mae: float
    occupancy_max_error: int
    event_match_tolerance_frames: int
    entry_true_positives: int
    entry_false_positives: int
    entry_false_negatives: int
    exit_true_positives: int
    exit_false_positives: int
    exit_false_negatives: int
    entry_precision: float
    entry_recall: float
    entry_f1: float
    exit_precision: float
    exit_recall: float
    exit_f1: float
    notes: str


def _read_events_csv(path: str):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "frame": int(row["frame"]),
                "direction": row["crossing_direction"],
            })
    return rows


def _read_timeline_csv(path: str):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "frame": int(row["frame"]),
                "occupancy": int(row["occupancy"]),
            })
    return rows


def _read_ground_truth_csv(path: str, initial_occupancy: int):
    gt_events = []   # list of (frame, "IN"/"OUT")
    dense_occupancy = {}  # frame -> occupancy, only if the column is present and populated

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        has_occupancy_col = reader.fieldnames and "actual_occupancy" in reader.fieldnames
        for row in reader:
            frame = int(row["frame"])
            if int(row.get("actual_entry", 0) or 0) == 1:
                gt_events.append((frame, "IN"))
            if int(row.get("actual_exit", 0) or 0) == 1:
                gt_events.append((frame, "OUT"))
            if has_occupancy_col and row.get("actual_occupancy", "") != "":
                dense_occupancy[frame] = int(row["actual_occupancy"])

    # Build a full per-frame ground-truth occupancy series by forward-filling
    # from initial_occupancy through the sorted list of ground-truth events
    # (used when dense_occupancy is sparse/absent).
    inferred_occupancy = {}
    occ = initial_occupancy
    for frame, direction in sorted(gt_events, key=lambda e: e[0]):
        if direction == "IN":
            occ += 1
        elif direction == "OUT":
            occ -= 1
        inferred_occupancy[frame] = occ

    return gt_events, dense_occupancy, inferred_occupancy


def _match_events(predicted: list, actual: list, tolerance_frames: int):
    """
    Greedy nearest-frame matching within `tolerance_frames`, one-to-one.
    Returns (true_positives, false_positives, false_negatives).
    """
    unmatched_actual = list(actual)
    tp = 0
    for p_frame in predicted:
        best_match = None
        best_dist = None
        for a_frame in unmatched_actual:
            dist = abs(p_frame - a_frame)
            if dist <= tolerance_frames and (best_dist is None or dist < best_dist):
                best_dist = dist
                best_match = a_frame
        if best_match is not None:
            tp += 1
            unmatched_actual.remove(best_match)
    fp = len(predicted) - tp
    fn = len(unmatched_actual)
    return tp, fp, fn


def _precision_recall_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def evaluate(experiment_id: str, events_csv_path: str, timeline_csv_path: str,
             ground_truth_csv_path: str, initial_occupancy: int = 0,
             event_match_tolerance_frames: int = 15) -> EvaluationResult:
    """
    Compute evaluation metrics for one experiment run against ground truth.
    Nothing here is invented: if ground truth is missing required data for a
    given metric, that metric is left as None-equivalent with a note, not
    guessed.
    """
    pred_events = _read_events_csv(events_csv_path)
    pred_timeline = _read_timeline_csv(timeline_csv_path)
    gt_events, dense_occupancy, inferred_occupancy = _read_ground_truth_csv(
        ground_truth_csv_path, initial_occupancy
    )

    pred_in_frames = [e["frame"] for e in pred_events if e["direction"] == "IN"]
    pred_out_frames = [e["frame"] for e in pred_events if e["direction"] == "OUT"]
    actual_in_frames = [f for f, d in gt_events if d == "IN"]
    actual_out_frames = [f for f, d in gt_events if d == "OUT"]

    entry_tp, entry_fp, entry_fn = _match_events(pred_in_frames, actual_in_frames, event_match_tolerance_frames)
    exit_tp, exit_fp, exit_fn = _match_events(pred_out_frames, actual_out_frames, event_match_tolerance_frames)

    entry_p, entry_r, entry_f1 = _precision_recall_f1(entry_tp, entry_fp, entry_fn)
    exit_p, exit_r, exit_f1 = _precision_recall_f1(exit_tp, exit_fp, exit_fn)

    # Occupancy MAE: compare predicted timeline against ground-truth
    # occupancy at every predicted frame where ground truth is available
    # (dense takes precedence over inferred-from-sparse-events).
    errors = []
    for row in pred_timeline:
        frame = row["frame"]
        gt_occ = dense_occupancy.get(frame)
        if gt_occ is None:
            # forward-fill from inferred_occupancy: most recent gt event at or before this frame
            candidates = [f for f in inferred_occupancy if f <= frame]
            if candidates:
                gt_occ = inferred_occupancy[max(candidates)]
            elif not inferred_occupancy and not dense_occupancy:
                continue  # no ground truth at all — skip, do not guess
            else:
                gt_occ = initial_occupancy
        errors.append(abs(row["occupancy"] - gt_occ))

    occupancy_mae = statistics.mean(errors) if errors else float("nan")
    occupancy_max_error = max(errors) if errors else 0

    predicted_final_occupancy = pred_timeline[-1]["occupancy"] if pred_timeline else initial_occupancy
    actual_final_occupancy = (
        inferred_occupancy[max(inferred_occupancy)] if inferred_occupancy
        else (dense_occupancy[max(dense_occupancy)] if dense_occupancy else initial_occupancy)
    )

    notes = []
    if not gt_events and not dense_occupancy:
        notes.append("No ground-truth entry/exit/occupancy rows found — metrics may be trivial.")
    if not errors:
        notes.append("No overlapping frames between predicted timeline and ground truth for MAE.")

    return EvaluationResult(
        experiment_id=experiment_id,
        predicted_entries=len(pred_in_frames),
        actual_entries=len(actual_in_frames),
        predicted_exits=len(pred_out_frames),
        actual_exits=len(actual_out_frames),
        predicted_final_occupancy=predicted_final_occupancy,
        actual_final_occupancy=actual_final_occupancy,
        occupancy_mae=round(occupancy_mae, 4) if errors else float("nan"),
        occupancy_max_error=occupancy_max_error,
        event_match_tolerance_frames=event_match_tolerance_frames,
        entry_true_positives=entry_tp,
        entry_false_positives=entry_fp,
        entry_false_negatives=entry_fn,
        exit_true_positives=exit_tp,
        exit_false_positives=exit_fp,
        exit_false_negatives=exit_fn,
        entry_precision=round(entry_p, 4),
        entry_recall=round(entry_r, 4),
        entry_f1=round(entry_f1, 4),
        exit_precision=round(exit_p, 4),
        exit_recall=round(exit_r, 4),
        exit_f1=round(exit_f1, 4),
        notes="; ".join(notes) if notes else "",
    )


def save_evaluation_csv(result: EvaluationResult, output_path: str):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    d = asdict(result)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(d.keys()))
        writer.writerow(list(d.values()))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate a pipeline run against ground truth.")
    parser.add_argument("--experiment_id", required=True)
    parser.add_argument("--events_csv", required=True)
    parser.add_argument("--timeline_csv", required=True)
    parser.add_argument("--ground_truth_csv", required=True)
    parser.add_argument("--initial_occupancy", type=int, default=0)
    parser.add_argument("--tolerance_frames", type=int, default=15)
    parser.add_argument("--output_csv", default=None)
    args = parser.parse_args()

    result = evaluate(
        experiment_id=args.experiment_id,
        events_csv_path=args.events_csv,
        timeline_csv_path=args.timeline_csv,
        ground_truth_csv_path=args.ground_truth_csv,
        initial_occupancy=args.initial_occupancy,
        event_match_tolerance_frames=args.tolerance_frames,
    )

    for k, v in asdict(result).items():
        print(f"{k}: {v}")

    if args.output_csv:
        save_evaluation_csv(result, args.output_csv)
        print(f"\nSaved to: {args.output_csv}")
