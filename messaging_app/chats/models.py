"""Imports for creating models"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class UserRole(models.TextChoices):
    """User role options: guest, host, admin"""

    GUEST = "guest", _("Guest")
    HOST = "host", _("Host")
    ADMIN = "admin", _("Admin")


class User(AbstractUser):
    """Custom user model with email authentication and additional fields."""

    user_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    first_name = models.CharField(
        max_length=150,
        null=False,
        blank=False,
    )
    last_name = models.CharField(
        max_length=150,
        null=False,
        blank=False,
    )
    email = models.EmailField(
        unique=True,
        null=False,
        blank=False,
    )

    # Phone number field
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    # Role field with choices
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.GUEST,
        null=False,
    )

    # Timestamp for when user was created
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    username = None
    password = models.CharField(
        max_length=120,
        verbose_name="password hash",
        null=False,
        blank=False,
    )

    # Use email as username field
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        """Class for defining user table constraints and indexes"""

        db_table = "user"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="unique_user_email")
        ]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Conversation(models.Model):
    """
    Model representing a conversation between multiple users.
    Uses many-to-many relationship to track participants.
    """

    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Many-to-many relationship with User model for participants
    participants = models.ManyToManyField(
        User,
        related_name="conversations",
        blank=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        "Class for defining conversation table name and index"

        db_table = "conversation"
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self):
        return f"Conversation {self.conversation_id}"


class ConversationParticipant(models.Model):
    """Links users to conversations they participate in."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="conversation_participants",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_conversations"
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        """Class for defining conversation_participant table"""

        db_table = "conversation_participant"
        unique_together = ["conversation", "user"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"], name="unique_conversation_particiapant"
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"


class Message(models.Model):
    """
    Model representing a message within a conversation.
    Links to User (sender) and Conversation.
    """

    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Foreign key to User model (sender)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        null=False,
        db_index=True,
    )

    # Foreign key to Conversation model
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        null=False,
        db_index=True,
    )

    # Message content
    message_body = models.TextField(null=False, blank=False)

    # Timestamp for when message was sent
    sent_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        """Class for defining message table indexes"""
        db_table = "message"
        ordering = ["sent_at"]
        indexes = [
            models.Index(fields=["sender", "sent_at"]),
            models.Index(fields=["conversation", "sent_at"]),
            models.Index(fields=["sent_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(message_body__isnull=False) & ~models.Q(message_body=''),
                name="message_body_not_empty"
            )
        ]

    def __str__(self):
        return f"Message from {self.sender} at {self.sent_at}"
