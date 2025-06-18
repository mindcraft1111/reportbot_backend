from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import GeminiTestView

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("test/", GeminiTestView.as_view(), name="prompt-test"),
    
]