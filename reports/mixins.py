from django.db import models
from django.utils import timezone


class ProjectStatusMixin(models.Model):
    class ProjectStatus(models.TextChoices):
        CREATED = ("created", "생성됨")
        IN_PROGRESS = ("in_progress", "리포트 생성 중")
        COMPLETED = ("completed", "완료됨")
        ERROR = ("error", "에러 발생")
        CANCELLED = ("cancelled", "사용자 취소")
        ARCHIVED = ("archived", "보관됨")

    status = models.CharField(max_length=100, choices=ProjectStatus.choices, default=ProjectStatus.CREATED)
    status_changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def set_status(self, status):
        self.status = status
        self.save(update_fields=["status"])

    def save(self, *args, **kwargs):
        if self.pk:
            orig = type(self).objects.get(pk=self.pk)
            if orig.status != self.status:
                self.status_changed_at = timezone.now()
        super().save(*args, **kwargs)


class ReportStatusMixin(models.Model):
    class ReportStatus(models.TextChoices):
        GENERATING = "generating", "생성 중"
        READY = "ready", "생성 완료"
        ERROR = "error", "오류 발생"
        VIEWED = "viewed", "사용자 확인 완료"
        ARCHIVED = "archived", "보관됨"
    
    status = models.CharField(max_length=100, choices=ReportStatus.choices, default=ReportStatus.GENERATING)

    class Meta:
        abstract = True

    def set_status(self, status):
        self.status = status
        self.save(update_fields=["status"])
    
    def is_ready(self):
        return self.status == self.ReportStatus.READY

    def get_status_message(self):
        return {
            self.ReportStatus.GENERATING: "리포트를 생성 중입니다...",
            self.ReportStatus.READY: "리포트 생성이 완료되었습니다!",
            self.ReportStatus.ERROR: "리포트 생성 중 오류가 발생했습니다.",
        }.get(self.status, "상태를 확인할 수 없습니다.")