from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export import resources, fields
from import_export.admin import ExportMixin
from .models import *
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.conf import settings
from django.utils.html import format_html


class CustomUserResource(resources.ModelResource):
    role_name = fields.Field(column_name='role')

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'mobile_number', 'cnic',
            'role_name', 'section_name', 'is_active', 'is_staff',
            'accepted_privacy_policy_at', 'accepted_community_policy_at',
            'is_deleted', 'deleted_at',
        )
        export_order = fields

    def dehydrate_role_name(self, obj):
        return obj.role.name if obj.role else ''


class CustomUserAdmin(ExportMixin, BaseUserAdmin):
    resource_classes = [CustomUserResource]
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ("id",'cnic', 'username', 'role',"profile_picture", 'is_staff', 'is_active', "section_name", "user_creator")
    list_filter = ('is_staff', 'is_active', 'role', "section_name")

    fieldsets = (
        (None, {'fields': ('mobile_number', 'password')}),
        ('Personal Info', {'fields': ('username', 'email', 'cnic', 'role', "section_name","profile_picture")}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile_number', 'password1', 'password2'),
        }),
    )

    search_fields = ('cnic', "username","mobile_number")
    ordering = ('id',)
    filter_horizontal = ('groups', 'user_permissions',)

    def save_model(self, request, obj, form, change):
        # Only set user_creator when creating a new user
        if not change and not obj.user_creator:
            obj.user_creator = request.user
        super().save_model(request, obj, form, change)



class AdminFarms(admin.ModelAdmin):
    autocomplete_fields  = ['created_by']
    list_display = ('id','created_by_username',"crop", "expert_advisory",'farm_name', 'bbox', 'created_at' ,"total_acres")
    search_fields = ('farm_name',"created_by__username","crop__name","crop_season__name")
    list_filter = ('created_at',"crop_season","crop")
    def created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else "-"

    created_by_username.short_description = "Created By"


    def expert_advisory(self, obj):
        if obj.crop and obj.crop.expert_advisory_pdf:
            return format_html(
                '<a href="{}" target="_blank">View PDF</a>',
                obj.crop.expert_advisory_pdf.url,
            )
        return "-"

    expert_advisory.short_description = "Expert Advisory"

    class Media:
        js = ['admin/js/custom_button_js.js',"admin/js/crop_filter.js"]

class AdminRole(admin.ModelAdmin):
    list_display = ("id",'name',"can_send_response",)
    search_fields = ("id",'name',)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Farms, AdminFarms)
admin.site.register(Role, AdminRole)
admin.site.register(CropDetails)


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("blocker__username", "blocker__mobile_number", "blocked__username", "blocked__mobile_number")
    raw_id_fields = ("blocker", "blocked")


@admin.register(UserBlockLog)
class UserBlockLogAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("blocker__username", "blocker__mobile_number", "blocked__username", "blocked__mobile_number")
    raw_id_fields = ("blocker", "blocked")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
