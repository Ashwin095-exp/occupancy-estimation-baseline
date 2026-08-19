"""
detection.py
------------
Person detection module. Wraps a pretrained Ultralytics YOLO model.

Deliberately does NOT use YOLO's built-in tracking (model.track()). We call
model.predict() for per-frame detection only, and hand the raw detections to
a separate tracking module (tracking.py). This keeps detection and tracking
as independently swappable components.

This module contains no original detection algorithm — it is a thin,
documented wrapper around Ultralytics' pretrained YOLO. The research
contribution of this project (when added) will NOT be in this module.

If the weights file given in config (detection.model_weights) does not
already exist at that path, Ultralytics will automatically download the
official pretrained weights from its GitHub release on first run. This
requires internet access once; after that, the local file is reused.
"""

from ultralytics import YOLO
import supervision as sv
import numpy as np


class PersonDetector:
    def __init__(self, model_weights: str, device: str, confidence_threshold: float,
                 iou_threshold: float, target_classes: list, input_image_size: int):
        self.model = YOLO(model_weights)
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.target_classes = target_classes
        self.input_image_size = input_image_size
        self.model_weights_name = model_weights

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """
        Run detection on a single frame.
        Returns a supervision.Detections object containing only the target
        classes (by default, COCO class 0 = person), already filtered by
        confidence and IoU thresholds from the config.
        """
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            classes=self.target_classes,
            imgsz=self.input_image_size,
            device=self.device,
            verbose=False,
        )[0]

        detections = sv.Detections.from_ultralytics(results)
        return detections
