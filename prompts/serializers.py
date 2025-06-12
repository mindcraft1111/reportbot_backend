from rest_framework import serializers
from api.models import Prompt, PromptTest


class PromptSerializer(serializers.ModelSerializer):
    section_id = serializers.SerializerMethodField()

    class Meta:
        model = Prompt
        fields = [
            "id",
            "name",
            "section_id",
            "prompt_text",
            "created_at"
        ]
        exclude = [
            "is_deleted",
            "deleted_at"
        ]
    
    def get_section_id(self, obj):
        return obj.section.section_id if obj.section else None


class PromptTestSerializer(serializers.Serializer):
    reviewer_name = serializers.SerializerMethodField()
    section_id = serializers.SerializerMethodField()

    class Meta:
        model = PromptTest
        fields = [
            "reviewer_name"
            "section_id",
            "prompt_text",
            "constraint_snapshot",
            "question",
            "answer",
            "passed",
            "reviewer_comment",
            "tested_at"
        ]
        exclude = [
            "is_deleted",
            "deleted_at"
        ]
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.user_name if obj.reviewer else "None"

    def get_section_id(self, obj):
        return obj.section.section_id if obj.section else None
