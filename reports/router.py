from .views import (
    ProjectViewSet,
    ReportViewSet,
    ReportTemplateViewSet,
    ReportSectionViewSet,
)


def register_report_routes(router):
    router.register(r"projects", ProjectViewSet)
    router.register(r"reports", ReportViewSet)
    router.register(r"report-template", ReportTemplateViewSet)
    router.register(r"report-sections", ReportSectionViewSet)
