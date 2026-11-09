# Shared dataset video storage

Dataset and DatasetVideo files use the dataset_videos Django storage alias. Assessment uploads, profile images, model artifacts, and static files keep their own storage. R2 stays private; browsers use existing protected Django endpoints. No public bucket domain or browser credentials are required.

Install backend requirements. Configure DATASET_R2_ENABLED=True, R2_ENDPOINT_URL, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_REGION=auto in backend environments. Use bucket-scoped object read/write credentials. Never put these in VITE variables. With R2 disabled, dataset storage uses MEDIA_ROOT.

## Existing files

1. Back up the dataset database and local media. Confirm local Django, Render, and workers point to the same intended database and bucket; storage does not synchronize database records.
2. Pause dataset writes and dataset workers. Apply Django migrations.
3. On the machine holding the original files, enable R2 and run `python manage.py migrate_dataset_videos --dry-run`. Use `--source-root <directory>` if originals live outside MEDIA_ROOT.
4. Run `python manage.py migrate_dataset_videos`. The command checks SHA-256 content, preserves object keys and local originals, skips identical objects, and fails for missing sources or conflicts. Conditional creation prevents overwriting an existing object. Single files above R2's single-PUT limit require a separate multipart migration. Rerun to verify all copies.
5. Enable R2 on Render and workers, restart all processes, and resume writes after smoke tests. Keep preview and ZIP import requests on the same backend: staging archives remain local and are not shared across instances or restarts.

## Verification

Upload a dataset locally, play and seek it through Render as an assigned annotator, then reverse the direction. Run dataset processing on a worker. Confirm expired tokens and unassigned users cannot play videos. Test a ZIP import and its resulting videos. Metadata and processing download remote videos to temporary disk; allow enough temporary space for the largest video.

Rollback to local storage only while writes remain paused and local originals cover every referenced object. New R2-only uploads must be copied back before disabling R2.
