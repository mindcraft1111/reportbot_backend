from django.db import models
from core.models.soft_delete import SoftDeleteMixin


class Prompt(SoftDeleteMixin):
    section = models.ForeignKey("ReportSection", on_delete=models.CASCADE, related_name="prompts")
    name = models.CharField(max_length=100, help_text="프롬프트 이름 (템플릿 섹션의 label)")
    prompt_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "prompt"

    def __str__(self):
        return f"{self.name} ({self.section.id})"


class PromptTest(models.Model):
    section = models.ForeignKey("ReportSection", on_delete=models.CASCADE, related_name="tests")
    prompt_text = models.TextField(verbose_name="테스트 프롬프트")
    constraint_snapshot = models.JSONField(blank=True, null=True, verbose_name="테스트시점 제약조건")
    question = models.TextField(max_length=500, verbose_name="생성 요청 질문")
    answer = models.TextField(verbose_name="AI 응답 결과")    
    passed = models.BooleanField(default=False, verbose_name="응답 적합 여부")
    reviewer_comment = models.TextField(blank=True, null=True, verbose_name="리뷰코멘트")
    tested_at = models.DateField(auto_now_add=True, verbose_name="테스트시간")

    class Meta:
        db_table = "prompt_test"