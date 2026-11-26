import json
from pathlib import Path

import cv2
import numpy as np

from apps.analytics.utils.file_resolver import resolved_video_path
from apps.datasets.models import DatasetSample


raw = json.loads(Path("debug_outputs/dataset_21_landmark_snapshot.json").read_text())
record = next(r for r in raw if r["sample_id"] == 697)
entry = record["frames"][len(record["frames"]) // 2]
sample = DatasetSample.objects.select_related("dataset_video").get(pk=697)
with resolved_video_path(sample.dataset_video.video_file) as path:
    capture = cv2.VideoCapture(path)
    capture.set(cv2.CAP_PROP_POS_FRAMES, entry["frame_index"])
    success, frame = capture.read()
    capture.release()
if not success:
    raise ValueError("Could not decode source frame.")
height, width = frame.shape[:2]
panels = []
for mapping in ("letterbox", "stretched"):
    image = frame.copy()
    points = {}
    scale = min(640 / width, 360 / height)
    pad_x = (640 - round(width * scale)) // 2
    pad_y = (360 - round(height * scale)) // 2
    for name, value in entry["landmarks"].items():
        x, y = value[:2]
        if mapping == "letterbox":
            x, y = (x / 2 - pad_x) / scale, (y / 2 - pad_y) / scale
        else:
            x, y = x * width / 1280, y * height / 720
        points[name] = (round(x), round(y))
    for side in ("left", "right"):
        for a, b in (("hip", "knee"), ("knee", "ankle")):
            cv2.line(image, points[f"{side}_{a}"], points[f"{side}_{b}"], (0, 0, 255), 5)
        for joint in ("hip", "knee", "ankle"):
            cv2.circle(image, points[f"{side}_{joint}"], 9, (0, 255, 0), -1)
    cv2.putText(image, mapping, (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    panels.append(cv2.resize(image, (405, 720)))
output = Path("debug_outputs/dataset_21_mapping_check.jpg")
cv2.imwrite(str(output), np.hstack(panels))
print(output.resolve())
