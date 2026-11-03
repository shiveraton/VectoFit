from .pipeline_config import DEFAULT_PREPROCESSING_CONFIG

LANDMARK_SCHEMA_VERSION = "landmarks_v2"
LEGACY_COORDINATE_SCALE = DEFAULT_PREPROCESSING_CONFIG.legacy_feature_coordinate_scale


def legacy_point(point, coordinate_scale=LEGACY_COORDINATE_SCALE):
    if isinstance(point, dict):
        return [
            float(point["x"]) * coordinate_scale,
            float(point["y"]) * coordinate_scale,
        ]
    return [float(point[0]) * coordinate_scale, float(point[1]) * coordinate_scale]


def legacy_frame(frame, coordinate_scale=LEGACY_COORDINATE_SCALE):
    landmarks = frame.get("landmarks", frame)
    return {
        name: legacy_point(point, coordinate_scale) for name, point in landmarks.items()
    }


def serialize_landmark_frames(entries):
    frames = []
    for entry in entries:
        landmarks = entry.get("landmarks") or {}
        frames.append(
            {
                "frame_index": int(entry["frame_index"]),
                "timestamp_ms": float(entry["timestamp_ms"]),
                "landmarks": {
                    name: {
                        "x": float(point.get("x_normalized", point["x"])),
                        "y": float(point.get("y_normalized", point["y"])),
                        "z": float(point["z"]),
                        "visibility": float(point["visibility"]),
                        "normalized": "x_normalized" in point,
                    }
                    for name, point in landmarks.items()
                },
            }
        )
    return {"schema_version": LANDMARK_SCHEMA_VERSION, "frames": frames}
