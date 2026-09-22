import uuid
import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_size_20mb(file):
    max_size = 20 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError("File size must be <= 20MB")


def post_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()

    # folder: community/user_12/
    folder = f"community/user_{instance.user.id}"

    # file: post_<postid>_<random>.ext (safe)
    return f"{folder}/{uuid.uuid4()}{ext}"


class CommunityPost(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts"
    )

    status = models.SmallIntegerField(
        default=1,
        db_index=True,
        help_text="1 = visible (default). 0 = hidden by admin.",
    )

    text = models.TextField(blank=True, null=True)

    image = models.ImageField(upload_to=post_upload_path, blank=True, null=True, validators=[validate_file_size_20mb])
    video = models.FileField(upload_to=post_upload_path, blank=True, null=True, validators=[validate_file_size_20mb])
    voice = models.FileField(upload_to=post_upload_path, blank=True, null=True, validators=[validate_file_size_20mb])

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post {self.id} by {self.user}"


class PostLike(models.Model):
    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} liked post {self.post.id}"


class PostComment(models.Model):
    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_comments"
    )

    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment {self.id} on Post {self.post.id}"


class CommentLike(models.Model):
    comment = models.ForeignKey(
        PostComment,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "user")

    def __str__(self):
        return f"{self.user} liked comment {self.comment.id}"


class ContentReport(models.Model):
    """
    A report raised by a user against a community post or comment.

    Exactly one of post/comment is set. Creating a report also hides the
    reported content from the reporter, so no separate "hidden" table is
    needed: the report itself is the hide record.
    """

    REASON_SPAM = "SPAM"
    REASON_HARASSMENT = "HARASSMENT"
    REASON_HATE_SPEECH = "HATE_SPEECH"
    REASON_VIOLENCE = "VIOLENCE"
    REASON_SEXUAL = "SEXUAL"
    REASON_MISINFORMATION = "MISINFORMATION"
    REASON_OTHER = "OTHER"

    REASON_CHOICES = [
        (REASON_SPAM, "Spam or misleading"),
        (REASON_HARASSMENT, "Harassment or bullying"),
        (REASON_HATE_SPEECH, "Hate speech"),
        (REASON_VIOLENCE, "Violence or threats"),
        (REASON_SEXUAL, "Nudity or sexual content"),
        (REASON_MISINFORMATION, "False or misleading information"),
        (REASON_OTHER, "Other"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_REVIEWED = "REVIEWED"
    STATUS_ACTION_TAKEN = "ACTION_TAKEN"
    STATUS_DISMISSED = "DISMISSED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending review"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_ACTION_TAKEN, "Action taken"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_reports",
    )

    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )

    comment = models.ForeignKey(
        PostComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )

    reason = models.CharField(max_length=20, choices=REASON_CHOICES, db_index=True)

    details = models.TextField(
        blank=True,
        default="",
        help_text="Required when the reason is Other.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports_reviewed",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderator_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content Report"
        verbose_name_plural = "Content Reports"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "post"],
                condition=models.Q(post__isnull=False),
                name="unique_content_report_reporter_post",
            ),
            models.UniqueConstraint(
                fields=["reporter", "comment"],
                condition=models.Q(comment__isnull=False),
                name="unique_content_report_reporter_comment",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(post__isnull=False, comment__isnull=True)
                    | models.Q(post__isnull=True, comment__isnull=False)
                ),
                name="content_report_exactly_one_target",
            ),
        ]

    def __str__(self):
        target = f"post {self.post_id}" if self.post_id else f"comment {self.comment_id}"
        return f"{self.reporter_id} reported {target} ({self.reason})"
