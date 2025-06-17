from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import gemini_streaming, GeminiStreamingView

router = DefaultRouter()
#router.register(r"templates", ReportTemplateViewSet)
#router.register(r"prompts", PromptViewSet)
#router.register(r"responses", PromptResponseViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("test/", GeminiStreamingView.as_view()),
    #path("analyze/", PromptAnalyzeAPIView.as_view(), name="analyze-prompt"),
    #path("test-create-template/", create_sample_report_template),
    #path("test-create-prompts/", create_structured_prompts),
    #path("analyze-all-prompts/", analyze_all_prompts),
]