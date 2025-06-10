from rest_framework import serializers
from .models import Prompt, PromptTest, UsedPrompt


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = "__all__"


class PromptTestSerializer(serializers.Serializer):
    class Meta:
        model = PromptTest
        fields = "__all__"


class UsedPromptSerializer(serializers.Serializer):
    class Meta:
        model = UsedPrompt
        fields = "__all__"
