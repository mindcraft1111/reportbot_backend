from rest_framework import serializers
from api.models.users import Users
from api.models.projects import (
    Projects,
    ReportTemplate,
    Report,
    ReportSection,
    ReportSectionResult,
)
from api.models.reviews import Products, Reviews
from api.models.utils.soft_delete import SoftDeleteSafeModelSerializer


class ProjectsSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = Projects


class ReportTemplateSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = ReportTemplate


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"


class ReportSectionSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = ReportSection


class ReportSectionResultSerializer(serializers.ModelSerializer):
    template_id = serializers.SerializerMethodField()

    class Meta:
        model = ReportSectionResult
        fields = ["template_id", "section_id", "label", "constraint", "created_at"]

    def get_template_id(self, obj):
        return obj.template.id if obj.template else None


class ProductsSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = Products


class ReviewsSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = Reviews




class UserSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = ("id", "email", "company", "position", "phone", "user_name", "projects", "join_date")

    def get_projects(self, obj):
        projects = obj.projects.all()
        return ProjectsSerializer(projects, many=True).data