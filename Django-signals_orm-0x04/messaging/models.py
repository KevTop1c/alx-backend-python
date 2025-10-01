"""Module imports for messaging.models"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from .managers import UnreadMessagesManager

User = settings.AUTH_USER_MODEL


# pylint: disable=no-member
class Message(models.Model):
    """Model to store messages between users"""

    MESSAGE_TYPES = [
        ("text", "Text"),
        ("image", "Image"),
        ("file", "File"),
    ]

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        help_text="User who sent the message",
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages",
        help_text="User who receives the message",
    )
    content = models.TextField(help_text="Message content")
    timestamp = models.DateTimeField(
        default=timezone.now, help_text="Time when message was sent"
    )
    is_read = models.BooleanField(
        default=False, help_text="Whether the message has been read"
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        default="text",
    )
    edited = models.BooleanField(default=False)
    parent_message = models.ForeignKey(
        "self",
        related_name="replies",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # Default manager
    objects = models.Manager()
    # Custom unread manager
    unread = UnreadMessagesManager()

    class Meta:
        """Meta class"""
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["receiver", "-timestamp"]),
            models.Index(fields=["sender", "-timestamp"]),
        ]

    def __str__(self):
        return f"Msg from {self.sender.username} to {self.receiver.username} at {self.timestamp}"


class MessageHistory(models.Model):
    """
    Model to store historical versions of edited messages.
    """

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="history"
    )
    old_message_body = models.TextField()
    old_message_type = models.CharField(
        max_length=10,
        choices=Message.MESSAGE_TYPES,
        default="text",
    )
    edited_at = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_edits",
    )

    class Meta:
        """Meta class"""
        db_table = "message_history"
        ordering = ["-edited_at"]
        indexes = [
            models.Index(fields=["message", "edited_at"]),
            models.Index(fields=["edited_by", "edited_at"]),
        ]
        verbose_name = "Message History"
        verbose_name_plural = "Message Histories"

    def __str__(self):
        return f"History for {self.message} edited at {self.edited_at}"

    def get_old_content_preview(self):
        """Get a preview of the old message content."""
        if not self.old_message_body:
            return ""
        body = str(self.old_message_body)
        return body if len(body) <= 50 else body[:50] + "..."


class Notification(models.Model):
    """Model to store notifications for users"""

    NOTIFICATION_TYPES = (
        ("message", "New Message"),
        ("system", "System Notification"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User who receives the notification",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        help_text="Related message if notification is about a message",
    )
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default="message"
    )
    content = models.TextField(help_text="Notification content/message")
    timestamp = models.DateTimeField(
        default=timezone.now, help_text="Time when notification was created"
    )
    is_read = models.BooleanField(
        default=False, help_text="Whether the notification has been read"
    )

    class Meta:
        """Meta class"""
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        content_value = str(self.content) if self.content is not None else ""
        return f"Notification for {self.user.username}: {content_value[:50]}"

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save()
