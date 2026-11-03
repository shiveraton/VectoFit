import hashlib
import json
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version


@dataclass(frozen=True)
class PreprocessingConfig:
    version: str = "fppa_pipeline_v1"
    target_fps: float = 30.0
    processing_width: int = 640
    processing_height: int = 360
    legacy_feature_coordinate_scale: float = 2.0
    resize_interpolation: str = "INTER_AREA"
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple[int, int] = (8, 8)
    denoise_enabled: bool = False
    denoise_h_luminance: int = 3
    denoise_photo_render: int = 3
    mediapipe_static_image_mode: bool = False
    mediapipe_model_complexity: int = 1
    mediapipe_smooth_landmarks: bool = True
    mediapipe_min_detection_confidence: float = 0.5
    mediapipe_min_tracking_confidence: float = 0.5
    mediapipe_enable_segmentation: bool = False
    orientation_policy: str = "opencv_decode_no_additional_rotation"
    filter_median_window: int = 3
    filter_savgol_window_seconds: float = 0.27
    filter_savgol_polyorder: int = 2
    visibility_threshold: float = 0.5
    valid_frame_fraction: float = 0.8
    min_rep_frames: int = 5
    min_phase_frames: int = 10
    min_descent_amplitude_px_at_1280x720: float = 35.0
    min_recovery_amplitude_px_at_1280x720: float = 35.0
    smoothing_window: int = 5
    duplicate_overlap_ratio: float = 0.0
    landmark_schema_version: str = "landmarks_v2"

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        payload = {"config": asdict(self), "runtime": runtime_versions()}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def runtime_versions() -> dict[str, str | None]:
    try:
        mediapipe_version = version("mediapipe")
    except PackageNotFoundError:
        mediapipe_version = None
    try:
        import cv2

        opencv_version = cv2.__version__
    except ImportError:
        opencv_version = None
    return {"mediapipe": mediapipe_version, "opencv": opencv_version}


DEFAULT_PREPROCESSING_CONFIG = PreprocessingConfig()
