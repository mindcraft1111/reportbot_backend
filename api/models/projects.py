# models/project.py
from django.db import models
from .users import Users
"""
CharField -> VARCHAR(N)
TextField -> TEXT 긴글 ex) 본문
"""
class Projects(models.Model):
    project_id = models.BigAutoField(primary_key=True, verbose_name='프로젝트아이디')
    id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='projects', verbose_name='인덱스')
    project_title = models.CharField(max_length=255, null=False, verbose_name='프로젝트명')
    description = models.CharField(max_length=255, null=False, verbose_name='프로젝트설명')
    created_at = models.CharField(max_length=55, null=False, verbose_name='프로젝트생성일')
    updated_at = models.CharField(max_length=55, null=True, verbose_name='프로젝트수정일')
    status = models.CharField(max_length=55, null=False, verbose_name='프로젝트상태')


    class Meta:
        db_table = 'projects'  # 테이블명 직접 지정
