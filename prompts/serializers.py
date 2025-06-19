from rest_framework import serializers

from api.models import Prompt, PromptTest


class PromptSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = Prompt
        fields = [
            "id",
            "category_display",
            "flag",
            "chunk_code",
            "prompt_text",
            "response_example",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PromptCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        exclude = ["is_deleted", "deleted_at"]


class PromptTestSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(
        source="reviewer.user_name", default="None", read_only=True
    )
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = PromptTest
        fields = [
            "id",
            "reviewer_name",
            "category_display",
            "chunk_code",
            "question",
            "answer",
            "passed",
            "reviewer_comment",
            "tested_at",
        ]


class PromptTestCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PromptTest
        fields = [
            "category",
            "chunk_code",
            "question",
            "answer",
            "passed",
            "reviewer_comment",
            "tested_at",
        ]
