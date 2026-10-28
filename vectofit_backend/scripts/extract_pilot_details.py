import cv2
from pathlib import Path

video = Path(r"media\datasets\videos\dd5d91c0df4e4cc2bd3d599c1060bbe8.mp4")
output_dir = Path("pilot_sample_340_detail_frames")
output_dir.mkdir(exist_ok=True)

cap = cv2.VideoCapture(str(video))

for frame_number in [246, 250, 270, 274]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()

    if not ok:
        print(f"Could not read frame {frame_number}")
        continue

    output_path = output_dir / f"frame_{frame_number}.jpg"
    cv2.imwrite(str(output_path), frame)
    print(output_path.resolve())

cap.release()
