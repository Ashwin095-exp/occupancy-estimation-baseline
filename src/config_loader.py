"""
config_loader.py
-----------------
Loads and validates the YAML configuration for a pipeline run.

Every experiment must be reproducible from its logged config alone. This
module is the single source of truth for reading that config, so there is
never a code path that silently uses a hard-coded parameter instead of the
config file.
"""

import yaml
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


@dataclass
class DetectionConfig:
    model_weights: str
    device: str
    confidence_threshold: float
    iou_threshold: float
    target_classes: List[int]
    input_image_size: int


@dataclass
class TrackerConfig:
    type: str
    bytetrack: dict
    botsort: dict

    def active_params(self) -> dict:
        """Return the parameter dict for whichever tracker `type` selects."""
        if self.type == "bytetrack":
            return dict(self.bytetrack)
        elif self.type == "botsort":
            return dict(self.botsort)
        else:
            raise ValueError(
                f"Unknown tracker type: {self.type!r} (expected 'bytetrack' or 'botsort')"
            )


@dataclass
class LineConfig:
    x1: float
    y1: float
    x2: float
    y2: float
    in_is_downward: bool


@dataclass
class OccupancyConfig:
    initial_occupancy: int
    clamp_minimum_zero: bool


@dataclass
class VideoConfig:
    source: str
    save_annotated_video: bool
    process_every_nth_frame: int


@dataclass
class LoggingConfig:
    output_dir: str
    save_raw_detections: bool


@dataclass
class PipelineConfig:
    experiment_id: str
    description: str
    video: VideoConfig
    detection: DetectionConfig
    tracker: TrackerConfig
    line: LineConfig
    occupancy: OccupancyConfig
    logging: LoggingConfig
    _source_path: str = field(default="", repr=False)


def load_config(config_path: str) -> PipelineConfig:
    """Load a YAML config file into a validated, typed PipelineConfig object."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    required_top_level = ["experiment", "video", "detection", "tracker", "line", "occupancy", "logging"]
    missing = [k for k in required_top_level if k not in raw]
    if missing:
        raise ValueError(f"Config is missing required sections: {missing}")

    cfg = PipelineConfig(
        experiment_id=raw["experiment"]["experiment_id"],
        description=raw["experiment"].get("description", ""),
        video=VideoConfig(**raw["video"]),
        detection=DetectionConfig(**raw["detection"]),
        tracker=TrackerConfig(
            type=raw["tracker"]["type"],
            bytetrack=raw["tracker"].get("bytetrack", {}),
            botsort=raw["tracker"].get("botsort", {}),
        ),
        line=LineConfig(**raw["line"]),
        occupancy=OccupancyConfig(**raw["occupancy"]),
        logging=LoggingConfig(**raw["logging"]),
        _source_path=str(path),
    )
    return cfg


def freeze_config_copy(config_path: str, output_dir: str, experiment_id: str) -> str:
    """
    Copy the exact config file used into the results directory for this run,
    so results can never be disconnected from the parameters that produced
    them. Returns the path to the frozen copy.
    """
    out_dir = Path(output_dir) / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{experiment_id}_config_used.yaml"
    shutil.copy(config_path, dest)
    return str(dest)
