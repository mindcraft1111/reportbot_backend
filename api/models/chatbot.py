from django.db import models
from .utils.soft_delete import SoftDeleteMixin


class ChatSession(SoftDeleteMixin):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="sessions")
    session_id = models.CharField(max_length=100, unique=True, verbose_name="세션ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user_name} - {self.session_id}"


class ChatMessage(SoftDeleteMixin):
    session = models.ForeignKey(ChatSession, related_name="messages", on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=[("user", "User"), ("ai", "AI")], verbose_name="채팅전송자")
    content = models.TextField(null=False, blank=False, verbose_name="메시지내용")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="타임스탬프")


class LangGraphLog(SoftDeleteMixin):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    node_name = models.CharField(max_length=100, null=True, verbose_name="노드명")
    input_summary = models.TextField(null=True, blank=True)
    output_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
