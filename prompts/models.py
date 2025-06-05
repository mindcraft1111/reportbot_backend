import uuid
from django.db import models


class ReportTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    structure_json = models.JSONField(help_text="리포트의 섹션 구성 및 순서 정의")
    # created_by = models.ForeignKey(
        # settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_templates"
    # )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Prompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="prompts"
    )
    section_id = models.CharField(max_length=100, help_text="structure_json 내 섹션 ID")
    prompt_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prompt for {self.section_id} in {self.template.name}"

class PromptResponse(models.Model):
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='responses')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
