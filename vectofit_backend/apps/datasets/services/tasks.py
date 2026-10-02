from celery import shared_task
from ..models import Dataset, DatasetSample
from apps.assessments.services.video_processor import VideoProcessor
from apps.assessments.services.pose_estimator import PoseEstimator
import logging
import os

logger = logging.getLogger(__name__)

@shared_task
def process_dataset_video_task(dataset_id):
    dataset = Dataset.objects.get(pk=dataset_id)
    dataset.status = 'PROCESSING'
    dataset.save(update_fields=['status'])
    
    logger.info(f"DEBUG: Starting task for dataset {dataset_id}")
    
    if not dataset.video_file:
        logger.error("DEBUG: No video file found for this dataset!")
        dataset.status = 'FAILED'
        dataset.error_message = "No video file found"
        dataset.save(update_fields=['status', 'error_message'])
        return

    logger.info(f"DEBUG: File path: {dataset.video_file.path}")
    logger.info(f"DEBUG: File exists on disk? {os.path.exists(dataset.video_file.path)}")

    try:
        logger.info("DEBUG: Calling VideoProcessor.process_video")
        result = VideoProcessor.process_video(dataset.video_file.path)
        logger.info(f"DEBUG: Process result status: {result.get('status')}")

        if result.get("status") == "success":
            logger.info(f"DEBUG: Success! Processed {result.get('processed_frames_count')} frames. Creating DatasetSample...")
            DatasetSample.objects.create(
                dataset=dataset,
                landmark_series=result.get("landmark_data", []),
                total_frames=result.get("processed_frames_count", 0)
            )
            dataset.status = 'READY'
        else:
            error_msg = result.get("message", "Unknown processing error")
            logger.error(f"DEBUG: Processor failed: {error_msg}")
            raise Exception(error_msg)
            
    except Exception as exc:
        logger.exception("DEBUG: Processing failed with exception")
        dataset.status = 'FAILED'
        dataset.error_message = str(exc)
    finally:
        dataset.save(update_fields=['status', 'error_message'])