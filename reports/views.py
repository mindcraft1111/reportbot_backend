from rest_framework import viewsets
from .models import Project, Report, ReportTemplate, ReportSection
from .serializers import (
    ProjectSerializer,
    ReportSerializer,
    ReportTemplateSerializer,
    ReportSectionSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer


class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer


class ReportSectionViewSet(viewsets.ModelViewSet):
    queryset = ReportSection.objects.all()
    serializer_class = ReportSectionSerializer
