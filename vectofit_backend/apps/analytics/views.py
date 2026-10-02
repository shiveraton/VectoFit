from datetime import timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from assessments.models import RepAssessment
from exercises.models import ExerciseVariant

from .serializers import (
    TrendPointSerializer,
    WeeklyTrendSerializer,
    VariantTrendSerializer,
)

def _reps_for_user(user):
    return RepAssessment.objects.filter(session__user=user)

class WeeklyTrendViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.isAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)

        reps = _reps_for_user(request.user)

        this_week = reps.filter(session__created_at__date__gte=week_start).aggregate(
            session_count=Count("session", distinct=True),
            rep_count=Count("id"),
            avg_hybrid_score=Avg("hybrid_score"),
        )
        previous_week = reps.filter(
            session__created_at__date__gte=previous_week_start,
            session__created_at__date__lt=week_start,
        ).aggregate(
            session_count=Count("session", distinct=True),
            rep_count=Count("id"),
            avg_hybrid_score=Avg("hybrid_score"),
        )

        data = {
            "week_start": week_start,
            "session_count": this_week["session_count"],
            "rep_count": this_week["rep_count"],
            "avg_hybrid_score": this_week["avg_hybrid_score"],
            "previous_week_session_count": previous_week["session_count"],
            "previous_week_rep_count": previous_week["rep_count"],
            "previous_week_avg_hybrid_score": previous_week["avg_hybrid_score"],
        }
        serializer = WeeklyTrendSerializer(data)
        return Response(serializer.data)

class TrendSeriesViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = request.query_params.get("period", "week")
        trunc_fn = TruncMonth if period == "month" else TruncWeek

        buckets = (
            _reps_for_user(request.user)
            .annotate(period_start=trunc_fn("session__created_at"))
            .values("period_start")
            .annotate(
                session_count=Count("session", distinct=True),
                rep_count=Count("id"),
                avg_hybrid_score=Avg("hybrid_score"),
            )
            .order_by("period_start")
        )

        serializer = TrendPointSerializer(buckets, many=True)
        return Response(serializer.data)

class VariantTrendViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, variant_id):
        variant = ExerciseVariant.objects.get(pk=variant_id)
        period = request.query_params.get("period", "week")
        trunc_fn = TruncMonth if period == "month" else TruncWeek

        buckets = (
            _reps_for_user(request.user)
            .filter(session__exercise_variant_id=variant_id)
            .annotate(period_start=trunc_fn("session__created_at"))
            .values("period_start")
            .annotate(
                session_count=Count("session", distinct=True),
                rep_count=Count("id"),
                avg_hybrid_score=Avg("hybrid_score"),
            )
            .order_by("period_start")
        )

        data = {
            "exercise_variant_id": variant.id,
            "exercise_variant_name": variant.name,
            "points": list(buckets),
        }
        serializer = VariantTrendSerializer
        return Response(serializer.data)