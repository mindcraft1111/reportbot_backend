import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "reportbot.settings"
)  # 프로젝트 이름 수정

import django

django.setup()

import json
from django.conf import settings
from api.models.projects import ReportTemplate


base_path = os.path.join(settings.BASE_DIR, "static")

# 파일 불러오기
with open(
    os.path.join(base_path, "templates", "report_var.html"), encoding="utf-8"
) as f:
    html_content = f.read()

with open(os.path.join(base_path, "css", "style.css"), encoding="utf-8") as f:
    css_content = f.read()

with open(os.path.join(base_path, "template_structure.json"), encoding="utf-8") as f:
    structure_json = json.load(f)

# 템플릿 생성
template = ReportTemplate.objects.create(
    name="샘플 리포트 템플릿",
    html_template=html_content,
    css_styles=css_content,
    structure_json=structure_json,
)

print("템플릿 저장 완료: ", template)
