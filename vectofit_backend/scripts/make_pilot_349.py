import cv2
import math
from pathlib import Path

video = Path(
    r"media\datasets\videos\46e2b248bb4546fb84db9a2b16df4d79.mp4"
)
output = Path("pilot_sample_349_contact_sheet.jpg")

cap = cv2.VideoCapture(str(video))
if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {video}")

start, end = 241, 276
indices = list(range(start, end + 1, 3))
if indices[-1] != end:
    indices.append(end)

tiles = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        continue

    frame = cv2.resize(frame, (320, 240))
    cv2.putText(
        frame, f"Frame {idx}", (8, 24),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2
    )
    tiles.append(frame)

cap.release()

if not tiles:
    raise RuntimeError("No frames extracted.")

cols = 3
rows = math.ceil(len(tiles) / cols)
blank = tiles[0].copy()
blank[:] = 35
tiles.extend([blank.copy() for _ in range(rows * cols - len(tiles))])

sheet = cv2.vconcat([
    cv2.hconcat(tiles[i * cols:(i + 1) * cols])
    for i in range(rows)
])

if not cv2.imwrite(str(output), sheet):
    raise RuntimeError("Could not save contact sheet.")

print(f"Saved: {output.resolve()}")
print(f"Frames: {indices}")
