from rest_framework import serializers
from .models import CommunityPost, ContentReport, PostComment
from .content_filter import is_abusive


class CommunityPostSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked_by_user = serializers.BooleanField(read_only=True)

    class Meta:
        model = CommunityPost
        fields = [
            "id",
            "user_id",
            "username",
            "text",
            "image",
            "video",
            "voice",
            "likes_count",
            "comments_count",
            "is_liked_by_user",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "user_id",
            "username",
            "likes_count",
            "comments_count",
            "is_liked_by_user",
            "created_at",
        ]

    def validate_text(self, value):
        if value and is_abusive(value):
            raise serializers.ValidationError(
                {
                    "message": (
                        "Your post contains language that is not allowed. "
                        "Please review our Community Usage Policy."
                    ),
                    "submitted_text": value,
                }
            )
        return value


class PostCommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    likes_count = serializers.IntegerField(read_only=True)
    is_liked_by_user = serializers.BooleanField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "post",
            "user_id",
            "username",
            "text",
            "likes_count",
            "is_liked_by_user",
            "created_at"
        ]
        read_only_fields = fields


class ContentReportSerializer(serializers.ModelSerializer):
    """Create a report against a post or a comment."""

    class Meta:
        model = ContentReport
        fields = ["id", "post", "comment", "reason", "details", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        post = attrs.get("post")
        comment = attrs.get("comment")

        if bool(post) == bool(comment):
            raise serializers.ValidationError("Provide exactly one of post or comment.")

        reason = attrs.get("reason")
        details = (attrs.get("details") or "").strip()

        if reason == ContentReport.REASON_OTHER and not details:
            raise serializers.ValidationError({
                "details": "Please describe the reason for your report."
            })

        attrs["details"] = details

        reporter = self.context["request"].user

        duplicate = ContentReport.objects.filter(
            reporter=reporter,
            post=post,
            comment=comment,
        ).exists()

        if duplicate:
            raise serializers.ValidationError("You have already reported this content.")

        return attrs
