from rest_framework import serializers

class WeeklyTrendSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    session_count = serializers.IntegerField()
    rep_count = serializers.IntegerField()
    avg_hybrid_score = serializers.FloatField(allow_null=True)

    previous_week_session_count = serializers.IntegerField()
    previous_week_rep_count = serializers.IntegerField()
    previous_week_avg_hybrid_score = serializers.FloatField(allow_null=True)

class TrendPointSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    session_count = serializers.IntegerField()
    rep_count = serializers.IntegerField()
    avg_hybrid_score = serializers.FloatField(allow_null=True)

class VariantTrendSerializer(serializers.Serializer):
    exercise_variant_id = serializers.IntegerField()
    exercise_variant_name = serializers.CharField()
    points = TrendPointSerializer(many=True)