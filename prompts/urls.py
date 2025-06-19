from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GeminiTestView, PromptTestViewset

router = DefaultRouter()


urlpatterns = [
    path("", include(router.urls)),
    path("test/", GeminiTestView.as_view(), name="prompt-test"),
]
