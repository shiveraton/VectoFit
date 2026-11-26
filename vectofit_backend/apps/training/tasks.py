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


@shared_task
def run_inference_task(run_id):
    import logging

    from django.db import transaction
    from django.utils import timezone

    from .models import InferenceRun, InferenceSimulation, InferenceStatus
    from .services.inference_simulation import prepare_simulation, run_simulation_model

    with transaction.atomic():
        run = InferenceRun.objects.select_for_update().get(pk=run_id)
        if run.status != InferenceStatus.PENDING:
            return run.status
        run.status = InferenceStatus.PROCESSING
        run.error_message = ""
        run.save(update_fields=["status", "error_message"])

    run = InferenceRun.objects.select_related("simulation", "model__training_job").get(
        pk=run_id
    )
    simulation = run.simulation
    try:
        if simulation.status != InferenceStatus.COMPLETED:
            simulation.status = InferenceStatus.PROCESSING
            simulation.error_message = ""
            simulation.save(update_fields=["status", "error_message"])
            prepare_simulation(simulation)
        run_simulation_model(run)
    except Exception as exc:
        logging.getLogger(__name__).exception("Inference failed for run=%s", run_id)
        now = timezone.now()
        InferenceRun.objects.filter(pk=run_id).update(
            status=InferenceStatus.FAILED,
            error_message=str(exc),
            completed_at=now,
        )
        if simulation.status != InferenceStatus.COMPLETED:
            InferenceSimulation.objects.filter(pk=simulation.pk).update(
                status=InferenceStatus.FAILED,
                error_message=str(exc),
                completed_at=now,
            )
        return InferenceStatus.FAILED
    return run.status
