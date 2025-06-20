# models/project.py
from django.db import models
from django.utils import timezone
from .users import Users
from .reviews import ProductCategory
from reports.mixins import ProjectStatusMixin, ReportStatusMixin
from .utils.soft_delete import SoftDeleteMixin

"""
CharField -> VARCHAR(N)
TextField -> TEXT 긴글 ex) 본문
"""
class Projects(ProjectStatusMixin, SoftDeleteMixin):
    project_id = models.BigAutoField(primary_key=True, verbose_name='프로젝트아이디')
    id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='projects', verbose_name='인덱스')
    project_title = models.CharField(max_length=255, null=False, verbose_name='프로젝트명')
    product_1 = models.ForeignKey("Products", on_delete=models.CASCADE, null=True, related_name="product_1", verbose_name="자사제품")
    product_2 = models.ForeignKey("Products", on_delete=models.CASCADE, null=True, related_name="product_2", verbose_name="경쟁사제품")
    description = models.CharField(max_length=255, null=False, verbose_name='프로젝트설명')
    created_at = models.CharField(max_length=55, null=False, verbose_name='프로젝트생성일')
    updated_at = models.CharField(max_length=55, null=True, verbose_name='프로젝트수정일')

    class Meta:
        db_table = "projects"  # 테이블명 직접 지정
    
    def save(self, *args, **kwargs):
        self.updated_at = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.project_title


class ReportTemplate(SoftDeleteMixin):
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
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="reports", verbose_name="사용자")
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, related_name="reports", verbose_name="프로젝트")
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, verbose_name="리포트템플릿번호")
    category = models.CharField(max_length=100, choices=ProductCategory.choices, null=True, verbose_name="상품 카테고리")
    title = models.CharField(max_length=200, blank=False, null=False, verbose_name="리포트제목")
    summary = models.CharField(max_length=500, blank=True, null=True, verbose_name="리포트요약결과")
    pdf_url = models.TextField(blank=True, null=True, verbose_name="pdf url")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="요청시간")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="완료시간")
    duration = models.DurationField(null=True, verbose_name="소요시간")


    def get_duration_in_minutes(self):
        return self.duration.total_seconds() / 60 # 분 단위로 표시

    def get_duration_in_hours(self):
        return self.duration.total_seconds() / 3600 # 시간 단위로 표시
 
    class Meta:
        db_table = "reports"

    def __str__(self):
        return self.title


# 리포트 각 항목 구조에 대한 메타정보
class ReportSection(SoftDeleteMixin):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="sections", verbose_name="참조템플릿")
    page_chunk = models.CharField(max_length=100, null=True, verbose_name="페이지 제목")
    section_id = models.CharField(max_length=100, blank=False, null=False, verbose_name="섹션코드")
    label = models.CharField(max_length=200, blank=False, null=False, verbose_name="섹션제목")
    constraint = models.JSONField(blank=True, null=True, verbose_name="제약조건")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_section"
        unique_together = ("template", "section_id")

    def __str__(self):
        return f"[{self.page_chunk} | {self.label}] {self.section_id}"


# 리포트 결과(섹션별 나눠서 저장)
class ReportSectionResult(ReportStatusMixin, SoftDeleteMixin):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="results")
    page_title = models.CharField(max_length=100, null=True, verbose_name="페이지네임")
    section_code = models.CharField(max_length=100, verbose_name="섹션코드") 
    content = models.JSONField(null=True, verbose_name="생성된 응답")
    constraint_snapshot = models.JSONField(blank=True, null=True, verbose_name="생성시점 제약조건") # snapshot
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_section_result"

    def __str__(self):
        return f"[{self.section_code}] {self.content[:10]}"