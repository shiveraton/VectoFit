import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.datasets.models import DatasetVideo
from apps.analytics.services.repetitions import extract_reps

video = DatasetVideo.objects.filter(
    dataset_id=17, view_angle__angle_variant='frontal', status='READY'
).first()
path = video.video_file.path
print('Video', video.pk, ':', path)
print('Exists:', os.path.exists(path))

extraction = extract_reps(path)
reps = extraction['reps']
print('Extracted', len(reps), 'reps:')
for i, rep in enumerate(reps):
    print('  idx=%d: start=%s, bottom=%s, end=%s, key_frame=%s' % (i, rep['start'], rep['bottom'], rep['end'], rep['key_frame_index']))