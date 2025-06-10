import uuid
from django.db import models
from core.models.soft_delete import SoftDeleteMixin
from reports.models import ReportTemplate


class Prompt(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey("ReportSection", on_delete=models.CASCADE, related_name="prompts")
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="prompts"
    )
    name = models.CharField(max_length=100, help_text="프롬프트 이름 (템플릿 섹션의 label)")
    prompt_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "prompt"

    def __str__(self):
        return f"{self.name} ({self.section_id})"

"""
class PromptResponse(models.Model):
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='responses')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
"""

class PromptTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name="tests")
    input_context = models.JSONField(verbose_name="전달한 입력값", help_text="예: 키워드, 분석 데이터")
    question = models.CharField(max_length=500, blank=False, null=False, verbose_name="질문")
    answer = models.TextField(blank=False, null=False, verbose_name="응답")
    reviewer_comment = models.TextField(blank=True, verbose_name="리뷰어평가")
    passed = models.BooleanField(default=False, verbose_name="통과여부")
    tested_at = models.DateField(auto_now=True, verbose_name="테스트시간")

    class Meta:
        db_table = "prompt_test"