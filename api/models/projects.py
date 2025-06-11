# models/project.py
from django.db import models
from .users import Users
from reports.mixins import ProjectStatusMixin, ReportStatusMixin
from core.models.soft_delete import SoftDeleteMixin

"""
CharField -> VARCHAR(N)
TextField -> TEXT 긴글 ex) 본문
"""
class Projects(ProjectStatusMixin, SoftDeleteMixin):
    project_id = models.BigAutoField(primary_key=True, verbose_name='프로젝트아이디')
    id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='projects', verbose_name='인덱스')
    project_title = models.CharField(max_length=255, null=False, verbose_name='프로젝트명')
    description = models.CharField(max_length=255, null=False, verbose_name='프로젝트설명')
    created_at = models.CharField(max_length=55, null=False, verbose_name='프로젝트생성일')
    updated_at = models.CharField(max_length=55, null=True, verbose_name='프로젝트수정일')

    class Meta:
        db_table = 'projects'  # 테이블명 직접 지정

    def __str__(self):
        return self.project_title


class ReportTemplate(SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True, verbose_name="리포트템플릿아이디")
    name = models.CharField(max_length=200, blank=False, null=False, verbose_name="템플릿명")
    html_template = models.TextField(blank=True, null=True, verbose_name="html코드")
    css_styles = models.TextField(blank=True, null=True, verbose_name="css코드")
    structure_json = models.JSONField(blank=True, null=True, verbose_name="템플릿구조", help_text="리포트 섹션 정의와 조건")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_template"

    def __str__(self):
        return self.name


class Report(ReportStatusMixin, SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True, editable=False, verbose_name="리포트아이디")
    user = models.ForeignKey("Users", on_delete=models.CASCADE, related_name="reports", verbose_name="사용자")
    project = models.ForeignKey("Projects", on_delete=models.CASCADE, related_name="projects", verbose_name="프로젝트")
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, verbose_name="리포트템플릿번호")
    title = models.CharField(max_length=200, blank=False, null=False, verbose_name="리포트제목")
    summary = models.CharField(max_length=500, blank=True, null=True, verbose_name="리포트요약결과")
    pdf_url = models.TextField(blank=True, null=True, verbose_name="pdf url")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="요청시간")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="완료시간")
    duration = models.DurationField(verbose_name="소요시간")

    def save(self, *args, **kwargs):
        if self.completed_at and not self.duration:
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


# 리포트 각 항목 구조에 대한 메타정보
class ReportSection(ReportStatusMixin, SoftDeleteMixin):
    id = models.BigAutoField(primary_key=True, editable=False, verbose_name="리포트섹션아이디")
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="sections", verbose_name="참조템플릿")
    section_id = models.CharField(max_length=100, blank=False, null=False, verbose_name="섹션코드")
    label = models.CharField(max_length=200, blank=False, null=False, verbose_name="섹션제목")
    constraint = models.JSONField(blank=True, null=True, verbose_name="제약조건")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_section"
        unique_together = ("template", "section_id")


# 리포트 결과(섹션별 나눠서 저장)
class ReportSectionResult(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    section = models.ForeignKey(ReportSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="참조섹션", related_name="results")
    section_id = models.CharField(max_length=100, blank=False, null=False, verbose_name="섹션코드") # snapshot
    label = models.CharField(max_length=200, blank=False, null=False, verbose_name="섹션제목") # snapshot
    content = models.TextField(verbose_name="생성된 응답")
    constraint_snapshot = models.JSONField(blank=True, null=True, verbose_name="생성시점 제약조건")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_section_result"