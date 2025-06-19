from django.utils import timezone
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


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ["id", "email", "company", "user_name"]


class ProjectsSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(source="id", read_only=True)
    product_1_name = serializers.CharField(source="product_1.product_name", read_only=True)
    product_2_name = serializers.CharField(source="product_2.product_name", read_only=True)
    
    class Meta:
        model = Projects
        fields = [
            "user",
            "project_id",
            "project_title",
            "product_1_name",
            "product_2_name",
            "description",
            "status",
            "status_changed_at",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["project_id", "status", "status_changed_at", "created_at", "updated_at"]


class ProjectsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = [
            "project_id",
            "project_title",
            "product_1",
            "product_2",
            "description",
            "created_at"
        ]
        read_only_fields=["project_id", "created_at"]
    
    def validate(self, attrs):
        if attrs["product_1"] == attrs["product_2"]:
            raise serializers.ValidationError("자사 제품과 경쟁사 제품은 서로 달라야 합니다.")
        return attrs
    
    def create(self, validated_data):
        validated_data["created_at"] = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        return Projects.objects.create(**validated_data)


class ProjectsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = [
            "project_title",
            "description",
        ]

class ReportTemplateSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = ReportTemplate


class ReportSerializer(serializers.ModelSerializer):
    project_id = serializers.CharField(source="project.project_id", read_only=True)
    report_contents = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "project_id",
            "category",
            "title",
            "summary",
            "report_contents",
            "pdf_url",
            "created_at",
            "completed_at",
            "duration"
        ]
        read_only_fields = ["id", "user", "project_id", "created_at", "completed_at", "duration"]
    
    def get_report_contents(self, obj):
        results = obj.results.all()
        return ReportSectionResultMiniSerializer(results, many=True).data


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "project",
            "template",
            "category",
            "title",
            "summary",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class ReportSectionSerializer(SoftDeleteSafeModelSerializer):
    class Meta(SoftDeleteSafeModelSerializer.Meta):
        model = ReportSection


class ReportSectionResultMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSectionResult
        fields = [
            "section_code",
            "label",
            "content"
        ]


class ReportSectionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSectionResult
        fields = [
            "id",
            "report",
            "prompt",
            "section",
            "section_code",
            "label",
            "content",
            "constraint_snapshot",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"] 


class ReportSectionResultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSectionResult
        fields = [
            "report",
            "section",
            "section_code",
            "label",
            "content",
            "constraint_snapshot",
            "created_at"
        ]


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