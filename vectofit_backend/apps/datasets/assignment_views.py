from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dataset, DatasetAnnotatorAssignment, DatasetAssignmentEvent, KneeAnnotation
from .services.assignments import review_samples, set_assignment


class AssignmentPagination(PageNumberPagination):
    page_size = 20


class StaffView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def paginated(self, request, rows, serialize):
        paginator = AssignmentPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([serialize(row) for row in page])


def user_data(user):
    return {"id": user.pk, "username": user.username}


class AnnotatorPickerView(StaffView):
    def get(self, request):
        users = get_user_model().objects.filter(
            is_active=True, is_staff=False, is_superuser=False, profile__is_annotator=True,
        ).order_by("username", "pk")
        search = request.query_params.get("search", "").strip()[:150]
        if search:
            users = users.filter(username__icontains=search)
        return self.paginated(request, users, user_data)


def eligible_dataset_samples(dataset):
    return review_samples().filter(dataset=dataset)


class AssignmentListView(StaffView):
    def get(self, request, dataset_id):
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        samples = eligible_dataset_samples(dataset)
        sample_count = samples.count()
        assignments = DatasetAnnotatorAssignment.objects.filter(dataset=dataset).select_related("annotator__profile").order_by("annotator__username", "pk")
        paginator = AssignmentPagination()
        page = paginator.paginate_queryset(assignments, request)
        # Select latest per sample/person, so edits and clear events do not inflate progress.
        latest = KneeAnnotation.objects.filter(
            sample_id=OuterRef("sample_id"), annotator_id=OuterRef("annotator_id"),
        ).order_by("-created_at", "-id").values("pk")[:1]
        reviewed = dict(KneeAnnotation.objects.filter(
            sample__in=samples, annotator_id__in=[row.annotator_id for row in page],
            pk=Subquery(latest), annotation__isnull=False,
        ).values("annotator_id").annotate(total=Count("pk")).values_list("annotator_id", "total"))
        rows = [{
            "id": row.pk, "annotator": user_data(row.annotator),
            "is_active": row.is_active, "assigned_at": row.assigned_at,
            "reviewed_count": reviewed.get(row.annotator_id, 0), "sample_count": sample_count,
            "account_eligible": bool(row.annotator.is_active and not row.annotator.is_staff and not row.annotator.is_superuser and getattr(getattr(row.annotator, "profile", None), "is_annotator", False)),
        } for row in page]
        response = paginator.get_paginated_response(rows)
        response.data["eligible_sample_count"] = sample_count
        response.data["all_annotators_access"] = dataset.all_annotators_access
        return response


class AssignmentStateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class DatasetAccessModeSerializer(serializers.Serializer):
    all_annotators_access = serializers.BooleanField()


class AssignmentDetailView(StaffView):
    def put(self, request, dataset_id, annotator_id):
        serializer = AssignmentStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        annotator = get_object_or_404(get_user_model().objects.select_related("profile"), pk=annotator_id)
        assignment = set_assignment(dataset, annotator, serializer.validated_data["is_active"], request.user)
        return Response({"id": assignment.pk if assignment else None, "is_active": assignment.is_active if assignment else False})


class DatasetAccessModeView(StaffView):
    def put(self, request, dataset_id):
        serializer = DatasetAccessModeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        dataset.all_annotators_access = serializer.validated_data["all_annotators_access"]
        dataset.save(update_fields=["all_annotators_access"])
        return Response({"all_annotators_access": dataset.all_annotators_access})


class AssignmentEventListView(StaffView):
    def get(self, request, dataset_id):
        get_object_or_404(Dataset, pk=dataset_id)
        events = DatasetAssignmentEvent.objects.filter(assignment__dataset_id=dataset_id).select_related("actor", "assignment__annotator")
        return self.paginated(request, events, lambda event: {
            "id": event.pk, "action": event.action, "created_at": event.created_at,
            "annotator": user_data(event.assignment.annotator),
            "actor": user_data(event.actor) if event.actor else None,
        })
