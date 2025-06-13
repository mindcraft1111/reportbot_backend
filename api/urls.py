from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView,
    LogoutView,
    LoginView,
    DeleteUserView,
    UpdateUserView,
    gemini_streaming,
)
from prompts.router import register_prompt_routes
from reports.router import register_report_routes

router = DefaultRouter()
register_prompt_routes(router)
register_report_routes(router)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="token_logout"),
    path("login/", LoginView.as_view(), name="token_obtain_pair"),
    path("del/", DeleteUserView.as_view(), name="delete-account"),
    path("update/", UpdateUserView.as_view(), name="update-account"),
    path("", include(router.urls)),
    path("ai/streaming/", gemini_streaming, name="gemini_streaming"),
]
