from django.urls import include, path
from rest_framework.routers import DefaultRouter


from . import views
from prompts.router import register_prompt_routes
from reports.router import register_report_routes

router = DefaultRouter()
register_prompt_routes(router)
register_report_routes(router)

urlpatterns = [
    path("", views.index, name="api_index"),
]
