import cv2


def apply_clahe(frame, clip_limit=2.0, tile_grid_size=(8, 8), clahe=None):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    if clahe is None:
        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=tile_grid_size,
        )

    enhanced_l_channel = clahe.apply(l_channel)
    lab_image = cv2.merge((enhanced_l_channel, a_channel, b_channel))

    return cv2.cvtColor(lab_image, cv2.COLOR_LAB2BGR)


def preprocess_frame(
    frame,
    h_luminance=3,
    photo_render=3,
    clahe=None,
):
    denoised_frame = cv2.fastNlMeansDenoisingColored(
        frame,
        None,
        h_luminance,
        photo_render,
    )

    return apply_clahe(denoised_frame, clahe=clahe)
