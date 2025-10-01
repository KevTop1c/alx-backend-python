"""Imports for creating models"""

import uuid
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a user with email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# Create your models here.
class UserRole(models.TextChoices):
    """User role options: guest, host, admin"""

    GUEST = "guest", _("Guest")
    HOST = "host", _("Host")
    ADMIN = "admin", _("Admin")


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email authentication and additional fields."""

    objects = CustomUserManager()

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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

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
        """Get user's full name"""
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

    # Optional conversation title/name
    title = models.CharField(max_length=255, null=True, blank=True)

    # Track if conversation is active
    is_active = models.BooleanField(default=True)

    class Meta:
        """Conversations table definition"""

        db_table = "conversations"
        indexes = [
            models.Index(fields=["conversation_id"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    # pylint: disable=no-member
    def __str__(self):
        if self.title:
            return f"Conversation: {self.title}"
        participants_names = ", ".join(
            [user.get_full_name() for user in self.participants.all()[:3]]
        )
        if self.participants.count() > 3:
            participants_names += f" and {self.participants.count() - 3} others"
        return f"Conversation between {participants_names}"

    def get_participant_count(self):
        """Return particpants total count"""
        return self.participants.count()

    def add_participant(self, user):
        """Add a user to the conversation."""
        self.participants.add(user)

    def remove_participant(self, user):
        """Remove a user from the conversation."""
        self.participants.remove(user)


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

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages",
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
    content = models.TextField(null=False, blank=False)

    # Timestamp for when message was sent
    timestamp = models.DateTimeField(
        auto_now_add=True,
    )

    # Optional: Track if message was edited
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    # Optional: Message type (text, image, file, etc.)
    class MessageType(models.TextChoices):
        """List of message types"""

        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"
        SYSTEM = "system", "System Message"

    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )

    class Meta:
        """Class for defining message table indexes"""

        db_table = "message"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["message_id"]),
            models.Index(fields=["conversation"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["sender", "timestamp"]),
            models.Index(fields=["conversation", "timestamp"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(content__isnull=False) & ~models.Q(content=""),
                name="message_body_not_empty",
            )
        ]

    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp}"

    def save(self, *args, **kwargs):
        # Ensure sender is a participant in the conversation
        # pylint: disable=no-member
        if self.conversation_id and self.sender_id:
            if not self.conversation.participants.filter(
                user_id=self.sender_id
            ).exists():
                raise ValueError("Sender must be a participant in the conversation")
        super().save(*args, **kwargs)

    def mark_as_edited(self):
        """Mark message as edited and update timestamp."""
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=["is_edited", "edited_at"])


# Additional model for tracking message read status (optional but useful)
class MessageReadStatus(models.Model):
    """
    Model to track which users have read which messages.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="read_status",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="message_reads",
    )

    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Class for defining message read status table"""

        db_table = "message_read_status"
        unique_together = ("message", "user")
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["user"]),
            models.Index(fields=["read_at"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} read message at {self.read_at}"  # pylint: disable=no-member


class Notification(models.Model):
    """Model for storing user notifications."""

    NOTIFICATION_TYPES = [
        ("new_message", "New Message"),
        ("message_read", "Message Read"),
        ("user_joined", "User Joined Conversation"),
        ("user_left", "User Left Conversation"),
    ]

    notification_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default="new_message"
    )

    title = models.CharField(max_length=255)

    message_content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Notification model definition"""

        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"Notification for {self.user}: {self.title}"

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.save()
