from celery import shared_task
import logging
from django.db import transaction
from django.utils import timezone

from .models import AssessmentSession
from .services.assessment_processor import (
    process_assessment_session as run_assessment_processing,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def process_assessment_session(self, session_id):
    with transaction.atomic():
        session = AssessmentSession.objects.select_for_update().get(pk=session_id)
        if session.status != AssessmentSession.Status.PENDING:
            return session.status
        session.status = AssessmentSession.Status.PROCESSING
        session.error_message = ""
        session.save(update_fields=["status", "error_message"])

    try:
        run_assessment_processing(session)
    except Exception as exc:
        logger.exception("Assessment task failed for session=%s", session_id)
        AssessmentSession.objects.filter(pk=session_id).update(
            status=AssessmentSession.Status.FAILED,
            error_message=str(exc),
            processed_at=timezone.now(),
        )
        session.refresh_from_db(fields=["status"])
    return session.status
