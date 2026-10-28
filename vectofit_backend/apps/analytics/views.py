from datetime import timedelta
from typing import ClassVar

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from apps.assessments.models import RepAssessment
from apps.exercises.models import ExerciseVariant

from .serializers import (
    DailyActivityPointSerializer,
    TrendPointSerializer,
    VariantTrendSerializer,
    WeeklyTrendSerializer,
)


def _reps_for_user(user):
    return RepAssessment.objects.filter(session__user=user)


def _daily_activity_for_user(user, week_start):
    week_end = week_start + timedelta(days=6)

    daily_rows = (
        _reps_for_user(user)
        .filter(
            session__created_at__date__range=(
                week_start,
                week_end,
            )
        )
        .annotate(date=TruncDate("session__created_at"))
        .values("date")
        .annotate(
            rep_count=Count("id"),
            session_count=Count("session_id", distinct=True),
        )
        .order_by("date")
    )

    activity_by_date = {row["date"]: row for row in daily_rows}

    return [
        {
            "date": day,
            "rep_count": activity_by_date.get(day, {}).get("rep_count", 0),
            "session_count": activity_by_date.get(day, {}).get("session_count", 0),
        }
        for day in (week_start + timedelta(days=offset) for offset in range(7))
    ]


class DailyActivityPointViewSet(viewsets.ViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def list(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

        daily_activity = _daily_activity_for_user(request.user, week_start)

        serializer = DailyActivityPointSerializer(daily_activity, many=True)

        return Response(serializer.data)


class WeeklyTrendViewSet(viewsets.ViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def list(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        week_end = week_start + timedelta(days=6)

        reps = _reps_for_user(request.user)

        this_week = reps.filter(
            session__created_at__date__range=(
                week_start,
                week_end,
            )
        ).aggregate(
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
        daily_activity = _daily_activity_for_user(request.user, week_start)

        data = {
            "week_start": week_start,
            "session_count": this_week["session_count"],
            "rep_count": this_week["rep_count"],
            "avg_hybrid_score": this_week["avg_hybrid_score"],
            "previous_week_session_count": previous_week["session_count"],
            "previous_week_rep_count": previous_week["rep_count"],
            "previous_week_avg_hybrid_score": previous_week["avg_hybrid_score"],
            "daily_activity": daily_activity,
        }
        serializer = WeeklyTrendSerializer(data)
        return Response(serializer.data)


class TrendSeriesViewSet(viewsets.ViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def list(self, request):
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


class VariantTrendViewSet(viewsets.ViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        variant = get_object_or_404(ExerciseVariant, pk=pk)
        period = request.query_params.get("period", "week")
        trunc_fn = TruncMonth if period == "month" else TruncWeek

        buckets = (
            _reps_for_user(request.user)
            .filter(session__exercise_variant_id=variant.pk)
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
            "exercise_variant_id": variant.pk,
            "exercise_variant_name": variant.name,
            "points": list(buckets),
        }

        serializer = VariantTrendSerializer(data)
        return Response(serializer.data)
