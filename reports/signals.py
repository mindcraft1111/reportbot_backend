from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import ReportTemplate, ReportSection
from django.utils import timezone


@receiver(post_save, sender=ReportTemplate)
def generate_report_sections_from_template(sender, instance, **kwargs):
    structure = instance.structure_json
    if not structure:
        return
    
    # 페이지 리스트가 배열인 경우
    pages = structure.get("pages", [])
    for page in pages:
        title = page.get("title")
        page_index = page.get("page_index")
        components = page.get("components", [])
        
        for component in components:
            section_code = component.get("var")
            if not section_code:
                continue # 코드 없는 경우 제외

            constraint_data = {k: v for k, v in component.items() if k!= "var"}

            ReportSection.objects.update_or_create(
                template=instance,
                section_id=section_code,
                defaults={
                    "label": component.get("description", f"섹션 {section_code}"),
                    "constraint": constraint_data,
                    "created_at": timezone.now(),
                },
            )