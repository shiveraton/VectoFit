from celery import shared_task

from .models import TrainingJob
from .services.run_training_job import run_training_job


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def run_training_job_task(self, job_id, **kwargs):
    job = TrainingJob.objects.get(pk=job_id)
    if job.status in {TrainingJob.Status.COMPLETED, TrainingJob.Status.FAILED}:
        return job.status
    run_training_job(job, **kwargs)
    return job.status
