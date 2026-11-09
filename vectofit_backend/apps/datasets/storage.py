from django.core.files.storage import storages


def dataset_video_storage():
    return storages["dataset_videos"]
