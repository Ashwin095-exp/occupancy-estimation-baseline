"""
main.py
-------
Orchestrates the baseline pipeline:

    Video -> PersonDetector -> PersonTracker -> LineCrossingDetector
          -> OccupancyEngine -> EventLogger

This file contains no detection, tracking, counting, or validation logic
itself — it only wires the independent modules together frame by frame.
That separation is what lets tracker backends or a future validation stage
swap in without touching this file's structure.

USAGE (run from the src/ directory):
    python main.py --config ../config/baseline_config.yaml
    python main.py --config ../config/baseline_config.yaml --experiment_id my_run_1
"""

import argparse
import time
from pathlib import Path
import cv2
import supervision as sv

from config_loader import load_config, freeze_config_copy
from detection import PersonDetector
from tracking import PersonTracker
from line_crossing import LineCrossingDetector
from occupancy import OccupancyEngine
from event_logger import EventLogger


def run_pipeline(config_path: str, experiment_id_override: str = None):
    cfg = load_config(config_path)
    experiment_id = experiment_id_override or cfg.experiment_id

    print(f"[CONFIG] Loaded config from {config_path}")
    print(f"[CONFIG] Experiment ID: {experiment_id}")

    # Freeze a copy of the config for reproducibility
    frozen_path = freeze_config_copy(config_path, cfg.logging.output_dir, experiment_id)
    print(f"[CONFIG] Frozen config copy saved to: {frozen_path}")

    # --- Open video ---
    cap = cv2.VideoCapture(cfg.video.source)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video source: {cfg.video.source}\n"
            f"Check that the path is correct relative to where you ran this "
            f"script (the config uses paths relative to the src/ directory)."
        )

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[VIDEO] {cfg.video.source} | {frame_width}x{frame_height} @ {fps:.2f} FPS | {total_frames} frames")

    # --- Initialize modules ---
    detector = PersonDetector(
        model_weights=cfg.detection.model_weights,
        device=cfg.detection.device,
        confidence_threshold=cfg.detection.confidence_threshold,
        iou_threshold=cfg.detection.iou_threshold,
        target_classes=cfg.detection.target_classes,
        input_image_size=cfg.detection.input_image_size,
    )

    tracker = PersonTracker(
        tracker_type=cfg.tracker.type,
        params=cfg.tracker.active_params(),
        frame_rate=fps,
    )
    print(f"[TRACKER] Using: {cfg.tracker.type}")

    line_detector = LineCrossingDetector(
        x1_norm=cfg.line.x1, y1_norm=cfg.line.y1,
        x2_norm=cfg.line.x2, y2_norm=cfg.line.y2,
        in_is_downward=cfg.line.in_is_downward,
        frame_width=frame_width, frame_height=frame_height,
    )

    occupancy_engine = OccupancyEngine(
        initial_occupancy=cfg.occupancy.initial_occupancy,
        clamp_minimum_zero=cfg.occupancy.clamp_minimum_zero,
    )

    logger = EventLogger(output_dir=cfg.logging.output_dir, experiment_id=experiment_id)

    # --- Annotators for QA video ---
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    line_annotator = sv.LineZoneAnnotator(thickness=2, text_scale=0.5)

    writer = None
    if cfg.video.save_annotated_video:
        annotated_dir = Path(cfg.logging.output_dir) / "annotated"
        annotated_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(annotated_dir / f"{experiment_id}_annotated.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (frame_width, frame_height))
        if not writer.isOpened():
            print(f"[WARNING] Could not open VideoWriter for {out_path} — annotated video will not be saved.")
            writer = None

    # --- Runtime tracking ---
    frame_idx = 0
    processing_start = time.time()
    frame_process_times = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % cfg.video.process_every_nth_frame != 0:
            frame_idx += 1
            continue

        t0 = time.time()
        timestamp = frame_idx / fps

        # 1. Detection
        detections = detector.detect(frame)

        # 2. Tracking
        tracked_detections = tracker.update(detections, frame=frame, timestamp=timestamp)

        # 3. Line crossing (conventional, unvalidated)
        crossing_events = line_detector.update(tracked_detections)

        # 4. Occupancy update + logging for each accepted crossing
        for event in crossing_events:
            new_occupancy = occupancy_engine.apply_event(event.direction)
            logger.log_event(
                frame=frame_idx, timestamp=timestamp, track_id=event.tracker_id,
                confidence=event.confidence, direction=event.direction,
                occupancy_after=new_occupancy,
            )

        # 5. Timeline logging (every processed frame)
        logger.log_timeline(
            frame=frame_idx, timestamp=timestamp,
            occupancy=occupancy_engine.occupancy,
            max_occupancy=occupancy_engine.max_occupancy_so_far,
        )

        # 6. Annotated frame for visual QA
        if writer is not None:
            labels = [
                f"ID {tid} {conf:.2f}" if tid != -1 else f"unconfirmed {conf:.2f}"
                for tid, conf in zip(tracked_detections.tracker_id, tracked_detections.confidence)
            ] if tracked_detections.tracker_id is not None else []
            annotated = box_annotator.annotate(scene=frame.copy(), detections=tracked_detections)
            annotated = label_annotator.annotate(scene=annotated, detections=tracked_detections, labels=labels)
            annotated = line_annotator.annotate(frame=annotated, line_counter=line_detector.line_zone)
            cv2.putText(annotated, f"Occupancy: {occupancy_engine.occupancy}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            writer.write(annotated)

        frame_process_times.append(time.time() - t0)
        frame_idx += 1

        if frame_idx % 100 == 0:
            print(f"[PROGRESS] Frame {frame_idx}/{total_frames} | Occupancy: {occupancy_engine.occupancy}")

    cap.release()
    if writer is not None:
        writer.release()
    logger.close()

    total_time = time.time() - processing_start
    avg_fps = frame_idx / total_time if total_time > 0 else 0
    avg_latency_ms = (sum(frame_process_times) / len(frame_process_times) * 1000) if frame_process_times else 0

    print("\n[SUMMARY]")
    print(f"  Frames processed:     {frame_idx}")
    print(f"  Total entries:        {occupancy_engine.total_entries}")
    print(f"  Total exits:          {occupancy_engine.total_exits}")
    print(f"  Final occupancy:      {occupancy_engine.occupancy}")
    print(f"  Max occupancy:        {occupancy_engine.max_occupancy_so_far}")
    print(f"  Processing time:      {total_time:.2f}s")
    print(f"  Avg processing FPS:   {avg_fps:.2f}")
    print(f"  Avg per-frame latency:{avg_latency_ms:.2f} ms")
    print(f"  Events log:           {logger.events_path}")
    print(f"  Timeline log:         {logger.timeline_path}")

    return {
        "frames_processed": frame_idx,
        "total_entries": occupancy_engine.total_entries,
        "total_exits": occupancy_engine.total_exits,
        "final_occupancy": occupancy_engine.occupancy,
        "max_occupancy": occupancy_engine.max_occupancy_so_far,
        "avg_fps": avg_fps,
        "avg_latency_ms": avg_latency_ms,
        "events_log_path": str(logger.events_path),
        "timeline_log_path": str(logger.timeline_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the baseline occupancy pipeline.")
    parser.add_argument("--config", type=str, required=True,
                         help="Path to YAML config file.")
    parser.add_argument("--experiment_id", type=str, default=None,
                         help="Override experiment_id from config (useful for batch runs).")
    args = parser.parse_args()

    run_pipeline(args.config, args.experiment_id)
