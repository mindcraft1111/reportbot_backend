
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("promptTest/", include("promptTest.urls")),
    path("prompt/", include("prompts.urls"))
]
