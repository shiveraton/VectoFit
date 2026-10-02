from django.db import models

# No models defined here on purpose.
#
# analytics computes aggregates live over assessments.RepAssessment /
# assessments.AssessmentSession rather than storing its own tables --
# see views.py for the query logic and the reasoning for this call
# (no background job infra yet to keep a cached/precomputed table
# fresh, and live aggregation is cheap at this data volume).
#
# If this app later needs cached/precomputed snapshots (e.g. once a
# Celery beat schedule exists), that's a model to add here -- the
# serializer output shape shouldn't need to change when that happens.