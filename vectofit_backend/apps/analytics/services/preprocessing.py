import cv2
"""preprocessing layer for individually derived frames from a squat movement"""

def apply_clahe(frame, clip_limit=2.0, tile_grid_size=(8, 8)):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clip_limit, tile_grid_size)
    enhanced_l_channel = clahe.apply(l_channel)

    lab_image = cv2.merge(
        (enhanced_l_channel, a_channel, b_channel)
    )

    enhanced_frame = cv2.cvtColor(lab_image, cv2.COLOR_LAB2BGR)

    return enhanced_frame

def preprocess_frame(frame, h_luminance=3, photo_render=3):
    denoised_frame = cv2.fastNlMeansDenoisingColored(
        frame,
        None,
        h_luminance,
        photo_render
    )

    processed_frame = apply_clahe(denoised_frame)

    return processed_frame

if __name__ == "__main__":
    frame = cv2.imread(r"D:\Thesis\VectoFit\vectofit_backend\apps\analytics\services\test_frame.jpg")

    print(frame.dtype)
    print(frame.shape)
    
    processed_frame = preprocess_frame(frame)

    cv2.imwrite("processed_frame.jpg", processed_frame)