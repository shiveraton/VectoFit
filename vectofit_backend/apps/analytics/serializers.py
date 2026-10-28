from rest_framework import serializers


class DailyActivityPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    rep_count = serializers.IntegerField()
    session_count = serializers.IntegerField()


class WeeklyTrendSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    session_count = serializers.IntegerField()
    rep_count = serializers.IntegerField()
    avg_hybrid_score = serializers.FloatField(allow_null=True)

    previous_week_session_count = serializers.IntegerField()
    previous_week_rep_count = serializers.IntegerField()
    previous_week_avg_hybrid_score = serializers.FloatField(allow_null=True)
    daily_activity = DailyActivityPointSerializer(many=True)


class TrendPointSerializer(serializers.Serializer):
    period_start = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    session_count = serializers.IntegerField()
    rep_count = serializers.IntegerField()


class VariantTrendSerializer(serializers.Serializer):
    exercise_variant_id = serializers.IntegerField()
    exercise_variant_name = serializers.CharField()
    points = TrendPointSerializer(many=True)
