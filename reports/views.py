from rest_framework import viewsets
from api.models import Users, Projects, Report, ReportTemplate, ReportSection, ReportSectionResult, Reviews, Products
from .serializers import (
    ProjectsSerializer,
    ReportSerializer,
    ReportTemplateSerializer,
    ReportSectionSerializer,
    ReportSectionResultSerializer,
    ProductsSerializer,
    ReviewsSerializer,
    UserSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.all()
    serializer_class = UserSerializer


class ProjectsViewSet(viewsets.ModelViewSet):
    queryset = Projects.objects.all()
    serializer_class = ProjectsSerializer


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer


class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer


class ReportSectionViewSet(viewsets.ModelViewSet):
    queryset = ReportSection.objects.all()
    serializer_class = ReportSectionSerializer

class ReportSectionResultViewSet(viewsets.ModelViewSet):
    queryset = ReportSectionResult.objects.all()
    serializer_class = ReportSectionResultSerializer


class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductsSerializer


class ReviewsViewSet(viewsets.ModelViewSet):
    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer