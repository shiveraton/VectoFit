# Backend dependency repair

Target: Windows x64, CPython 3.11.9. Repair date: 2026-11-12.

## Diagnosis and choices

The root `.venv` contained NumPy 2.2.6, SciPy 1.15.3 and
opencv-python-headless 4.11.0.86, but no MediaPipe or JAX. `pip check`
passed because it checks installed distribution metadata, not missing project
requirements or native imports. The repository requirements differed from this environment.
There are also separate `vectofit_backend/.venv` and `.venv_broken` directories;
this repair uses only the root `.venv`.

| Package | Previous requirement | Repaired requirement | Reason |
| --- | --- | --- | --- |
| NumPy | 2.4.6 | 1.26.4 | Conservative NumPy 1.x baseline verified with the full smoke test; NumPy 2 introduces a C ABI transition but is not proven broken here. |
| SciPy | 1.17.1 | 1.15.3 | Conservative compatible baseline, also matching the previous installed SciPy. Both releases support Python 3.11; 1.17.1 is not inherently incompatible with 1.26.4. |
| JAX / jaxlib | 0.10.2 | 0.4.30 | JAX 0.10.2 requires NumPy >=2; 0.4.30 accepts NumPy 1.26.4 and SciPy 1.15.3. Matched jaxlib has a CPython 3.11 Windows CPU wheel. |
| ml_dtypes | 0.6.0 | 0.5.3 | Verified NumPy 1.26-compatible release and Windows wheel; required by JAX. This is not a claim that 0.6.0 is broken. |
| OpenCV contrib | 4.11.0.86 | unchanged | Required by MediaPipe; Python 3.11 requires NumPy >=1.23.5. Use exactly one OpenCV distribution. |
| MediaPipe | 0.10.14 | unchanged | Retains the application's `mp.solutions.pose` API and pose model behavior. Requires protobuf >=4.25.3,<5. |

Compatibility was checked against version-specific PyPI JSON metadata and wheel
availability, then against actual installation and execution. Saved metadata and
wheel hashes are in `backend-dependency-metadata.json`. Metadata alone cannot
prove native ABI compatibility.

Sources:
- https://numpy.org/doc/stable/user/troubleshooting-importerror.html
- https://pypi.org/pypi/mediapipe/0.10.14/json
- https://pypi.org/pypi/opencv-contrib-python/4.11.0.86/json
- https://pypi.org/pypi/jax/0.4.30/json
- https://pypi.org/pypi/jax/0.10.2/json
- https://pypi.org/pypi/scipy/1.15.3/json
- https://pypi.org/pypi/scipy/1.17.1/json

The previously unpinned transitive packages botocore 1.43.127, jmespath 1.1.0,
s3transfer 0.19.3 and urllib3 2.8.0 are now pinned to the resolved versions.
`.gitignore` exposes this report and excludes the archived environment.

## Reproduction

From the repository root in PowerShell, with CPython 3.11 x64 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r vectofit_backend/requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe vectofit_backend/scripts/smoke_dependencies.py
```

Create the environment at its final path; Windows venv entry points contain
absolute paths. Use the root `.venv/Scripts/python.exe` as the IDE interpreter.
Close terminals using an older interpreter and activate `.venv` again.
Do not install another OpenCV wheel alongside opencv-contrib-python.
`requirements-production.txt` includes the repaired requirements and adds Gunicorn;
production Linux execution is a separate validation target.

## Preservation and rollback

The old root environment is preserved at `.venv_before_dependency_repair`.
It is archival: scripts may contain the original `.venv` absolute path.
Its package list is `.cache/dependencies-before-repair.txt`.
The fresh installation report and log are `.cache/dependency-install-report.json`
and `.cache/dependency-install.log`.
No application source, settings, datasets, model artifacts, database, or research
protocol was modified. No migrations or real training jobs were run.
The smoke script uses synthetic data and an in-memory SQLite database; its
XGBoost persistence test writes only inside a temporary directory.
It tests execution and repeatable serialization, not research validity or accuracy.

## Verified results

- Clean installation completed successfully. PowerShell labeled pip's stderr
  update notice as NativeCommandError; the log confirms installation success.
  Subsequent checks captured subprocess exit codes directly.
- `pip check`: no broken requirements.
- Every requirement pin matches installed metadata; exactly one OpenCV package.
- Native imports include MediaPipe, OpenCV, SciPy, JAX, pandas, scikit-learn,
  XGBoost, FilterPy, Celery, boto3, psycopg2 and django-storages.
- SciPy Savitzky-Golay filtering, JAX JIT arithmetic, OpenCV JPEG encoding/color
  conversion, bundled MediaPipe Pose inference on a blank frame, and synthetic
  XGBoost fitting plus save/load prediction equality all passed.
- Django system checks: zero issues. Eight existing training-configuration tests
  passed, including repeatability and grouped-fold behavior. Smoke exit code: 0.
- Production requirements dry-run: exit 0; only Gunicorn 23.0.0 would be added.
  This does not verify a running Linux/Gunicorn deployment.
- Independently tested MediaPipe 0.10.14 with the archived NumPy 2.2.6 using
  import and actual Pose execution: exit 0. No NumPy 2 ABI error was reproduced.
  Thus this repair must not be cited as proof that NumPy 2 universally fails with
  this MediaPipe wheel. The confirmed original failure was missing MediaPipe;
  neither MediaPipe nor JAX was installed. The selected NumPy 1.x baseline is
  conservative, and changing to it requires the older compatible JAX pins.
- SciPy 1.17.1 and ml_dtypes 0.6.0 were not shown to be defective. Their changes
  select a verified baseline rather than resolve independently proven bugs.

The complete original NumPy 2.4.6/JAX 0.10.2 requirement set was not rebuilt
and executed. Existing trained artifacts and real-video research outcomes were
not revalidated; dependency repair does not establish numerical equivalence
between environments. Keep recording `training_environment()` with experiments.
Native MediaPipe feedback warnings appeared but did not fail inference.

Local logs: `.cache/dependency-smoke.log`,
`.cache/dependency-production-resolve.log`, and
`.cache/dependency-numpy2-reproduction.log`.

Bootstrap tools used: pip 24.0, setuptools 65.5.0.
