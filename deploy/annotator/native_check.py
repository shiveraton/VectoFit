#!/usr/bin/env python3
"""Run inside the actual ARM server venv before enabling services."""

import platform
import sys


def main():
    if platform.machine().lower() not in {"aarch64", "arm64"}:
        sys.exit("Run this check on the Oracle ARM host.")
    if sys.version_info[:2] != (3, 11):
        sys.exit("This deployment profile requires Python 3.11.")
    import cv2
    import jax
    import mediapipe as mp
    import numpy as np
    import scipy
    import sklearn
    import xgboost
    from filterpy.kalman import KalmanFilter

    # Exercise native libraries and the legacy MediaPipe API used by VectoFit.
    assert cv2.cvtColor(
        np.zeros((8, 8, 3), dtype=np.uint8), cv2.COLOR_BGR2RGB
    ).shape == (8, 8, 3)
    with mp.solutions.pose.Pose(static_image_mode=True) as pose:
        pose.process(np.zeros((64, 64, 3), dtype=np.uint8))
    assert KalmanFilter(dim_x=2, dim_z=1).dim_x == 2
    assert jax.numpy.ones(1).shape == (1,)
    print(
        {
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "mediapipe": mp.__version__,
            "opencv": cv2.__version__,
            "sklearn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "status": "native imports and minimal execution passed",
        }
    )
    print(
        "Next: validate existing model loading and one authorized video-processing job."
    )


if __name__ == "__main__":
    main()
