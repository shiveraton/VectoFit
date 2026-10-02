
# VectoFit

VectoFit is a computer vision–based squat exercise movement quality assessment system developed as an undergraduate Computer Science thesis. The system analyzes squat movements from a single camera using pose estimation and biomechanical feature extraction to provide objective feedback on exercise quality.

## Features

* Real-time human pose estimation
* Joint angle analysis
* Range of motion (ROM) assessment
* Kinematic velocity tracking
* Bilateral asymmetry detection
* Repetition counting
* Movement quality assessment
* Web-based dashboard for monitoring assessment results

## Tech Stack

### Backend

* Python
* Django
* Django REST Framework

### Computer Vision & Machine Learning

* MediaPipe
* OpenCV
* NumPy
* Pandas
* XGBoost (planned)
* Rule-Based System

### Frontend

* Angular
* Ionic

## Project Structure

```text
vectofit_backend/
├── apps/
├── config/
├── data/
├── docs/
├── logs/
├── scripts/
├── tests/
├── requirements.txt
├── README.md
└── manage.py
```

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd vectofit_backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate the virtual environment.

**Windows**

```bash
.venv\Scripts\activate
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and configure the required environment variables.

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create an administrator account

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The application will be available at:

```
http://127.0.0.1:8000/
```

## Development

Whenever new database models are added:

```bash
python manage.py makemigrations
python manage.py migrate
```

If new packages are installed:

```bash
pip freeze > requirements.txt
```

## Current Status

VectoFit is currently under active development as part of an undergraduate thesis. Features, architecture, and documentation may change as the project progresses.

## License

This project is intended for academic and research purposes.
