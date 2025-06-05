from rest_framework import serializers
from .models import ReportTemplate, Prompt, PromptResponse

class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = '__all__'

class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = '__all__'

class PromptResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptResponse
        fields = '__all__'
