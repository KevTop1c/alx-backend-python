"""Module imports for Admin"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Conversation, Message, MessageReadStatus


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for the User model.
    Extends Django's built-in UserAdmin with additional fields.
    """

    # Fields to display in the user list
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "phone_number",
        "is_active",
        "date_joined",
        "created_at",
    )

    # Fields that can be searched
    search_fields = ("email", "first_name", "last_name", "phone_number")

    # Filters in the right sidebar
    list_filter = ("role", "is_active", "is_staff", "date_joined", "created_at")

    # Fields to display when editing a user
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "phone_number", "role")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields to display when adding a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    # Use email as the ordering field
    ordering = ("email",)

    # Read-only fields
    readonly_fields = ("user_id", "date_joined", "last_login", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin interface for the Conversation model.
    """

    list_display = (
        "conversation_id_short",
        "title",
        "participant_count",
        "is_active",
        "created_at",
        "latest_message_preview",
    )

    list_filter = ("is_active", "created_at")
    search_fields = (
        "title",
        "participants__email",
        "participants__first_name",
        "participants__last_name",
    )
    filter_horizontal = ("participants",)
    readonly_fields = ("conversation_id", "created_at")

    def conversation_id_short(self, obj):
        """Display shortened conversation ID for better readability."""
        return str(obj.conversation_id)[:8] + "..."

    conversation_id_short.short_description = "ID"

    def participant_count(self, obj):
        """Display the number of participants in the conversation."""
        return obj.get_participant_count()

    participant_count.short_description = "Participants"

    def latest_message_preview(self, obj):
        """Display a preview of the latest message in the conversation."""
        latest_message = obj.messages.order_by("-sent_at").first()
        if latest_message:
            preview = latest_message.message_body[:50]
            if len(latest_message.message_body) > 50:
                preview += "..."
            return format_html("<em>{}</em>", preview)
        return "No messages"

    latest_message_preview.short_description = "Latest Message"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin interface for the Message model.
    """

    list_display = (
        "message_id_short",
        "sender",
        "conversation_preview",
        "message_preview",
        "message_type",
        "sent_at",
        "is_edited",
    )

    list_filter = ("message_type", "is_edited", "sent_at", "sender__role")
    search_fields = (
        "message_body",
        "sender__email",
        "sender__first_name",
        "sender__last_name",
        "conversation__title",
    )
    readonly_fields = ("message_id", "sent_at", "edited_at")

    # Organize fields in the edit form
    fieldsets = (
        (None, {"fields": ("sender", "conversation", "message_body", "message_type")}),
        (
            "Timestamps",
            {"fields": ("sent_at", "is_edited", "edited_at"), "classes": ("collapse",)},
        ),
        ("System", {"fields": ("message_id",), "classes": ("collapse",)}),
    )

    def message_id_short(self, obj):
        """Display shortened message ID for better readability."""
        return str(obj.message_id)[:8] + "..."

    message_id_short.short_description = "ID"

    def conversation_preview(self, obj):
        """Display conversation title or participants."""
        if obj.conversation.title:
            return obj.conversation.title
        return f"Conversation {str(obj.conversation.conversation_id)[:8]}..."

    conversation_preview.short_description = "Conversation"

    def message_preview(self, obj):
        """Display message preview."""
        preview = obj.message_body[:100]
        if len(obj.message_body) > 100:
            preview += "..."
        return preview

    message_preview.short_description = "Message"


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    """
    Admin interface for the MessageReadStatus model.
    """

    list_display = ("id_short", "user", "message_preview", "read_at")

    list_filter = ("read_at", "user__role")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "message__message_body",
    )
    readonly_fields = ("id", "read_at")

    def id_short(self, obj):
        """Display shortened ID for better readability."""
        return str(obj.id)[:8] + "..."

    id_short.short_description = "ID"

    def message_preview(self, obj):
        """Display message preview."""
        preview = obj.message.message_body[:50]
        if len(obj.message.message_body) > 50:
            preview += "..."
        return preview

    message_preview.short_description = "Message"


# Customize admin site headers
admin.site.site_header = "Messaging App Administration"
admin.site.site_title = "Messaging Admin"
admin.site.index_title = "Welcome to Messaging App Administration"
