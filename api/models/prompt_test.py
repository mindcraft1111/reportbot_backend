from django.db import models
from .utils.soft_delete import SoftDeleteMixin
from .reviews import ProductCategory


class Prompt(SoftDeleteMixin):
    category = models.CharField(max_length=100, choices=ProductCategory.choices, null=True, verbose_name="카테고리")
    flag = models.CharField(max_length=10, null=True, verbose_name="그래프, 텍스트 여부")
    chunk_code = models.CharField(max_length=100, null=True, verbose_name="C코드")
    prompt_text = models.TextField(verbose_name="프롬프트")
    response_example = models.TextField(null=True, verbose_name="응답 예시")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "prompt"

    def __str__(self):
        return f"[{self.category}] {self.chunk_code}"


class PromptTest(models.Model):
    reviewer = models.ForeignKey("Users", on_delete=models.CASCADE, related_name="tests", verbose_name="테스터")
    category = models.CharField(max_length=100, choices=ProductCategory.choices, null=True, verbose_name="카테고리")
    chunk_code = models.CharField(max_length=100, null=True, verbose_name="C코드")
    question = models.TextField(verbose_name="생성 요청 질문")
    answer = models.TextField(verbose_name="AI 응답 결과")    
    passed = models.BooleanField(default=False, verbose_name="응답 적합 여부")
    reviewer_comment = models.TextField(blank=True, null=True, verbose_name="리뷰코멘트")
    tested_at = models.DateField(auto_now_add=True, verbose_name="테스트시간")

    class Meta:
        db_table = "prompt_test"
        ordering = ["-tested_at"]
    
    def __str__(self):
        return f"[{self.reviewer.user_name}] {self.chunk_code}"