# VectoFit

VectoFit is a thesis system for squat movement assessment. It contains a Django REST API and video/ML processing backend, a React Native mobile app, and a Vue 3 administrative console.

## Repository layout

- `vectofit_backend/` — Django API, assessment and dataset processing, analytics, and model training.
- `vectofit_frontend/` — React Native mobile app with camera based assessment.
- `vectofit_admin/` — Vue 3 and TypeScript admin console.

## Local development

### Backend

1. Create and activate a Python virtual environment, then install `vectofit_backend/requirements.txt`.
2. Copy `vectofit_backend/.env.example` to `vectofit_backend/.env`. Replace `SECRET_KEY`; set `DEBUG=True` for local work. The example uses SQLite and a local Redis broker.
3. Start Redis, then from `vectofit_backend/` run `python manage.py migrate` and `python manage.py runserver`.
4. In a second backend terminal, run `celery -A config worker --pool=solo --loglevel=info` (the solo pool is suitable for local Windows development).

For a deployed environment set `DEBUG=False` and provide explicit `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`. Never reuse the example secret key.

### Mobile app

1. From `vectofit_frontend/`, copy `.env.example` to `.env` and set `VECTOFIT_API_URL` to the backend API root, including `/api`.
2. Install JavaScript dependencies with `npm ci`, start Metro with `npm start`, then use `npm run android` or `npm run ios`.
3. Use `http://10.0.2.2:8000/api` for the standard Android emulator, `http://127.0.0.1:8000/api` for the iOS simulator, or the development computer’s LAN address for a physical device.

Metro reads the environment file when it starts. Restart Metro after changing the URL.

### Admin console

From `vectofit_admin/`, run `npm ci` and `npm run dev`. Its API base URL and local login/setup details should be configured for the selected backend environment.

## Data handling status

See [DATA_HANDLING.md](DATA_HANDLING.md) for current access boundaries, retention behavior, and remaining deployment decisions.

## Project status

This is an academic research system under active development. Movement metrics and model predictions should be interpreted within the validation and limitations documented by the thesis; the repository does not establish clinical validation or a production deployment configuration.
