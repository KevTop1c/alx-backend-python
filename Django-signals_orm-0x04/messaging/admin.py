from django.contrib import admin
from .models import Message, Notification


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model"""

    list_display = [
        "id",
        "sender",
        "receiver",
        "content_preview",
        "timestamp",
        "is_read",
    ]
    list_filter = ["is_read", "timestamp", "sender", "receiver"]
    search_fields = ["sender__username", "receiver__username", "content"]
    readonly_fields = ["timestamp"]
    date_hierarchy = "timestamp"

    fieldsets = (
        ("Message Details", {"fields": ("sender", "receiver", "content")}),
        ("Metadata", {"fields": ("timestamp", "is_read"), "classes": ("collapse",)}),
    )

    def content_preview(self, obj):
        """Display a preview of the message content"""
        return obj.content[:50] + ("..." if len(obj.content) > 50 else "")

    content_preview.short_description = "Content Preview"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("sender", "receiver")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model"""

    list_display = [
        "id",
        "user",
        "notification_type",
        "content_preview",
        "timestamp",
        "is_read",
    ]
    list_filter = ["is_read", "notification_type", "timestamp", "user"]
    search_fields = ["user__username", "content"]
    readonly_fields = ["timestamp"]
    date_hierarchy = "timestamp"

    fieldsets = (
        (
            "Notification Details",
            {"fields": ("user", "notification_type", "message", "content")},
        ),
        (
            "Status",
            {
                "fields": ("timestamp", "is_read"),
            },
        ),
    )

    def content_preview(self, obj):
        """Display a preview of the notification content"""
        return obj.content[:50] + ("..." if len(obj.content) > 50 else "")

    content_preview.short_description = "Content Preview"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("user", "message")

    actions = ["mark_as_read", "mark_as_unread"]

    def mark_as_read(self, request, queryset):
        """Admin action to mark notifications as read"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notifications marked as read.")

    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        """Admin action to mark notifications as unread"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notifications marked as unread.")

    mark_as_unread.short_description = "Mark selected notifications as unread"
