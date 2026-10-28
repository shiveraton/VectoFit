import cv2
import math
from pathlib import Path

video = Path(
    r"media\datasets\videos\dd5d91c0df4e4cc2bd3d599c1060bbe8.mp4"
)
output = Path("pilot_sample_340_contact_sheet.jpg")

cap = cv2.VideoCapture(str(video))
if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {video}")

total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"Video frames: {total}, FPS: {fps:.2f}")

start, end = 230, 287
if end >= total:
    raise ValueError(f"Frame {end} exceeds video length ({total} frames)")

# Sample the full repetition at evenly spaced frame positions.
indices = list(range(start, end + 1, 4))
if indices[-1] != end:
    indices.append(end)

tiles = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        print(f"Warning: could not read frame {idx}")
        continue

    frame = cv2.resize(frame, (320, 240))
    cv2.putText(
        frame, f"Frame {idx}", (8, 24),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2
    )
    tiles.append(frame)

cap.release()

if not tiles:
    raise RuntimeError("No frames were extracted.")

cols = 3
rows = math.ceil(len(tiles) / cols)
blank = tiles[0].copy()
blank[:] = 35
tiles.extend([blank.copy() for _ in range(rows * cols - len(tiles))])

grid = [
    cv2.hconcat(tiles[r * cols:(r + 1) * cols])
    for r in range(rows)
]
sheet = cv2.vconcat(grid)

if not cv2.imwrite(str(output), sheet):
    raise RuntimeError("Could not save contact sheet.")

print(f"Saved: {output.resolve()}")
print(f"Frames included: {indices}")
