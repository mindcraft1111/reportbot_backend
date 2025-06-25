from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from api.models import (
    Users,
    Projects,
    Report,
    ReportTemplate,
    ReportSection,
    ReportSectionResult,
    Reviews,
    Products,
)
from api.models.utils.response import api_response
from .serializers import (
    ProjectsSerializer,
    ProjectsCreateSerializer,
    ProjectsUpdateSerializer,
    ReportSerializer,
    ReportCreateSerializer,
    ReportTemplateSerializer,
    ReportSectionSerializer,
    ReportSectionResultSerializer,
    ReportSectionResultCreateSerializer,
    ProductsSerializer,
    ReviewsSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)


class ProjectsViewSet(viewsets.ModelViewSet):
    queryset = Projects.objects.all()
    serializer_class = ProjectsSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        리스트·디테일 공통으로 가장 최근 1개만 반환.
        """
        # ↓ 필요 시 다른 정렬·필터 넣기
        return Projects.objects.order_by("created_at")[:1]

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectsCreateSerializer

        if self.action == "partial_update":
            return ProjectsUpdateSerializer
        return ProjectsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(id=request.user)
        return api_response(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(user=request.user)

        # 프로젝트 상태 변경
        report.project.set_status(Projects.ProjectStatus.IN_PROGRESS)
        return api_response(data=serializer.data, status_code=201)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = (IsAuthenticated,)


class ReportSectionViewSet(viewsets.ModelViewSet):
    queryset = ReportSection.objects.all()
    serializer_class = ReportSectionSerializer
    permission_classes = (IsAuthenticated,)


class ReportSectionResultViewSet(viewsets.ModelViewSet):
    queryset = ReportSectionResult.objects.all()
    serializer_class = ReportSectionResultSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return ReportSectionResultCreateSerializer
        return ReportSectionResultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(data=serializer.data, status_code=201)


class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductsSerializer


class ReviewsViewSet(viewsets.ModelViewSet):
    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    permission_classes = (IsAuthenticated,)
