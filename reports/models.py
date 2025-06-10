import uuid
from django.db import models
from mixins import ProjectStatusMixin, ReportStatusMixin
from core.models.soft_delete import SoftDeleteMixin


class Project(ProjectStatusMixin, SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 사용자 아이디
    # user = 
    title = models.CharField(max_length=30, blank=False, null=False, verbose_name="프로젝트명")
    description = models.CharField(max_length=100, blank=True, verbose_name="프로젝트설명")
    report_count = models.PositiveIntegerField(default=0, verbose_name="생성된 리포트 수")
    last_accessed_at = models.DateTimeField(null=True, blank=True, verbose_name="최근 열람일자")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project"

    def __str__(self):
        return self.title



class ReportTemplate(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, blank=False, null=False, verbose_name="템플릿명")
    html_template = models.TextField(blank=True, null=True, verbose_name="html코드")
    css_styles = models.TextField(blank=True, null=True, verbose_name="css코드")
    structure_json = models.JSONField(blank=True, null=True, verbose_name="템플릿구조")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_template"

    def __str__(self):
        return self.name



class Report(ReportStatusMixin, SoftDeleteMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 사용자 아이디
    # user = 
    # 프로젝트 번호
    # project = 
    ################
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, verbose_name="리포트템플릿번호")
    title = models.CharField(max_length=200, blank=False, null=False, verbose_name="리포트제목")
    summary = models.CharField(max_length=500, blank=True, null=True, verbose_name="리포트요약결과")
    pdf_url = models.TextField(blank=True, null=True, verbose_name="pdf url")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="요청시간")
    completed_at = models.DateTimeField(auto_now=True, verbose_name="요청시간")
    duration = models.DurationField(verbose_name="소요시간")

    def save(self, *args, **kwargs):
        self.duration = self.completed_at - self.created_at
        super().save(*args, *kwargs)
    
    def get_duration_in_minutes(self):
        return self.duration.total_seconds() / 60 # 분 단위로 표시

    def get_duration_in_hours(self):
        return self.duration.total_seconds() / 3600 # 시간 단위로 표시

    def set_pdf_url(self, url):
        self.pdf_url = url
        super().save(update_fields=["pdf_url"])
    
    class Meta:
        db_table = "reports"


class ReportSection(ReportStatusMixin, SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, verbose_name="리포트번호")
    section_id = models.CharField(max_length=100, blank=False, null=False, verbose_name="섹션코드")
    label = models.CharField(max_length=200, blank=False, null=False, verbose_name="섹션제목")
    html_code = models.TextField(blank=True, null=True, verbose_name="섹션html코드")
    constraint = models.CharField(max_length=200, blank=True, null=True, verbose_name="제약조건")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_section"



class UsedPrompt(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="used_prompts")
    prompt = models.ForeignKey("Prompt", on_delete=models.PROTECT, related_name="used_in_reports")
    prompt_version = models.CharField(max_length=20, blank=True, verbose_name="사용된 프롬프트 버전")
    response = models.TextField(verbose_name="AI 응답 결과")
    section_id = models.CharField(max_length=100, blank=True, verbose_name="적용된 섹션코드")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "used_prompt"





