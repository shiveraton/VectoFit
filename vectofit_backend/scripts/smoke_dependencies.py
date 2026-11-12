import importlib
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(
    DJANGO_SETTINGS_MODULE="config.settings",
    SECRET_KEY="dependency-smoke-only",
    DEBUG="True",
    DATABASE_URL="sqlite:///:memory:",
    DATASET_R2_ENABLED="False",
    SECURE_SSL_REDIRECT="False",
)

import cv2
import django
import jax
import jax.numpy as jnp
import mediapipe as mp
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

from importlib.metadata import distributions, version
from packaging.requirements import Requirement

requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
for line in requirements.read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    requirement = Requirement(line)
    assert version(requirement.name) in requirement.specifier, requirement.name
opencv_packages = {
    distribution.metadata["Name"].lower()
    for distribution in distributions()
    if distribution.metadata["Name"].lower().startswith("opencv-")
}
assert opencv_packages == {"opencv-contrib-python"}, opencv_packages
for module in ("filterpy.kalman", "celery", "boto3", "psycopg2", "storages"):
    importlib.import_module(module)

for package in ("numpy", "scipy", "opencv-contrib-python", "mediapipe", "jax", "jaxlib", "scikit-learn", "xgboost"):
    print(f"{package}=={version(package)}", flush=True)

assert np.allclose(savgol_filter(np.arange(9.0), 5, 2), np.arange(9.0))
assert int(jax.jit(lambda x: jnp.sum(x * x))(jnp.arange(4))) == 14
frame = np.zeros((256, 256, 3), dtype=np.uint8)
assert cv2.imencode(".jpg", frame)[0]
assert cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).shape == frame.shape
with mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1) as pose:
    assert pose.process(frame).pose_landmarks is None
assert pd.DataFrame({"value": np.arange(4)}).value.sum() == 6

features = np.array([[0, 0], [0, 1], [1, 0], [1, 1]] * 8, dtype=float)
labels = np.array([0, 0, 1, 1] * 8)
model = XGBClassifier(n_estimators=8, max_depth=2, n_jobs=1, random_state=42)
model.fit(features, labels)
assert accuracy_score(labels, model.predict(features)) == 1.0
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "smoke.json"
    model.save_model(path)
    restored = XGBClassifier()
    restored.load_model(path)
    assert np.array_equal(model.predict(features), restored.predict(features))

django.setup()
from django.conf import settings
from django.core.management import call_command
assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
assert settings.DATABASES["default"]["NAME"] == ":memory:"
call_command("check")
for module in (
    "apps.assessments.services.pose_estimator",
    "apps.analytics.services.fppa",
    "apps.training.services.trainer",
    "apps.training.services.model_inference",
):
    importlib.import_module(module)
call_command("test", "apps.training.test_configuration", verbosity=1, interactive=False)
print("Dependency, native ML, Django, and training configuration smoke checks passed.")
