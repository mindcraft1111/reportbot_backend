from django.db import models
from .users import Users

class Prompt_test(models.Model):
    code = models.CharField(max_length=50, primary_key=True, verbose_name='인식코드')    
    product_name = models.CharField(max_length=255, null=False, verbose_name='제품명')  
    question = models.CharField(max_length=255, null=False, verbose_name='질문')     
    answer = models.CharField(max_length=255, null=False, verbose_name='답변')        
    
    class Meta:
        db_table = 'prompt_test'  # 테이블명 직접 지정