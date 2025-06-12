from .views import (
    UserViewSet,
    ProjectsViewSet,
    ReportViewSet,
    ReportTemplateViewSet,
    ReportSectionViewSet,
    ReportSectionResultViewSet,
    ProductsViewSet,
    ReviewsViewSet,
)


def register_report_routes(router):
    router.register(r"members", UserViewSet)
    router.register(r"projects", ProjectsViewSet)
    router.register(r"reports", ReportViewSet)
    router.register(r"report-template", ReportTemplateViewSet)
    router.register(r"report-sections", ReportSectionViewSet)
    router.register(r"report-sections-result", ReportSectionResultViewSet)
    router.register(r"products", ProductsViewSet)
    router.register(r"reviews", ReviewsViewSet)
