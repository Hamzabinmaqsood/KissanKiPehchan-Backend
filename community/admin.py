from django.contrib import admin
from django.utils import timezone

from .models import CommunityPost, PostLike, PostComment, CommentLike, ContentReport


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "text", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "text")
    list_editable = ("status",)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    list_filter = ("created_at",)


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "text", "created_at")
    list_filter = ("created_at",)


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "user", "created_at")
    list_filter = ("created_at",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mark_reviewed(queryset, request, status_value):
    """
    Update every report in the queryset to the given status and stamp
    reviewed_by / reviewed_at.  Returns (updated_count, hidden_count).
    """
    now = timezone.now()
    updated = queryset.update(
        status=status_value,
        reviewed_by=request.user,
        reviewed_at=now,
    )
    return updated


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

@admin.action(description="✅ Approve selected reports — hide post from everyone")
def approve_reports(modeladmin, request, queryset):
    """
    ACTION_TAKEN:
      - Mark reports as action taken
      - Set post.status = 0 so the post is hidden from ALL users
    """
    # Collect post ids before updating (queryset changes after update)
    post_ids = list(
        queryset.filter(post__isnull=False).values_list("post_id", flat=True).distinct()
    )

    _mark_reviewed(queryset, request, ContentReport.STATUS_ACTION_TAKEN)

    hidden = 0
    if post_ids:
        hidden = CommunityPost.objects.filter(id__in=post_ids).update(status=0)

    modeladmin.message_user(
        request,
        f"{queryset.count()} report(s) approved. "
        f"{hidden} post(s) hidden from all users.",
    )


@admin.action(description="❌ Dismiss selected reports — keep post visible to others")
def dismiss_reports(modeladmin, request, queryset):
    """
    DISMISSED:
      - Mark reports as dismissed
      - post.status is NOT changed — post stays visible to everyone
        except the reporter (their ContentReport row still filters it out)
    """
    count = _mark_reviewed(queryset, request, ContentReport.STATUS_DISMISSED)
    modeladmin.message_user(
        request,
        f"{count} report(s) dismissed. "
        "Posts remain visible to all users except the original reporter.",
    )


@admin.action(description="🔍 Mark selected reports as reviewed (no action)")
def mark_reviewed(modeladmin, request, queryset):
    count = _mark_reviewed(queryset, request, ContentReport.STATUS_REVIEWED)
    modeladmin.message_user(request, f"{count} report(s) marked as reviewed.")


# ---------------------------------------------------------------------------
# ContentReport admin
# ---------------------------------------------------------------------------

@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "reporter", "post", "comment", "reason",
        "status", "created_at", "reviewed_by", "reviewed_at",
    )
    list_filter = ("status", "reason", "created_at")
    search_fields = (
        "reporter__username", "reporter__mobile_number",
        "details", "moderator_notes",
    )
    raw_id_fields = ("reporter", "post", "comment", "reviewed_by")
    readonly_fields = ("created_at", "updated_at")

    actions = [approve_reports, dismiss_reports, mark_reviewed]

    # -----------------------------------------------------------------------
    # Auto-apply action when saving a single report via the detail form
    # -----------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        """
        When an admin manually edits a report and saves it:
          - If status changed to ACTION_TAKEN → hide the post (status = 0)
          - If status changed to DISMISSED   → no post change
          - Set reviewed_by / reviewed_at if not already set
        """
        if change and "status" in form.changed_data:
            if obj.status == ContentReport.STATUS_ACTION_TAKEN:
                if obj.post:
                    CommunityPost.objects.filter(id=obj.post_id).update(status=0)
                if not obj.reviewed_by:
                    obj.reviewed_by = request.user
                if not obj.reviewed_at:
                    obj.reviewed_at = timezone.now()

            elif obj.status == ContentReport.STATUS_DISMISSED:
                if not obj.reviewed_by:
                    obj.reviewed_by = request.user
                if not obj.reviewed_at:
                    obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)
