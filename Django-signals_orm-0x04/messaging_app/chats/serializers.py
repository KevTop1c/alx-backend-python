"""Import for Serializers"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.timesince import timesince
from .models import (
    User,
    Conversation,
    ConversationParticipant,
    Message,
    MessageReadStatus,
    Notification,
)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with password handling and validation.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    full_name = serializers.SerializerMethodField()

    class Meta:
        """User model serializer configuration"""

        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "created_at",
            "password",
            "password_confirm",
            "full_name",
        ]
        read_only_fields = ["user_id", "created_at"]
        extra_kwargs = {"email": {"required": True}}

    def get_full_name(self, obj):
        """Return the user's full name."""
        return obj.get_full_name()

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        """Create a new user with encrypted password."""
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")

        # Use email as username if username not provided
        if not validated_data.get("username"):
            validated_data["username"] = validated_data["email"]

        user = User.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        """Update user instance, handling password separately."""
        password = validated_data.pop("password", None)
        validated_data.pop("password_confirm", None)

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update password if provided
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UserSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for user summary info in nested relationships.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        """User Summary configuration"""

        model = User
        fields = ["user_id", "email", "first_name", "last_name", "full_name", "role"]
        read_only_fields = ["user_id", "email", "first_name", "last_name", "role"]

    def get_full_name(self, obj):
        """ "Get user's full name"""
        return obj.get_full_name()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model with sender information and validation."""

    sender = UserSummarySerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True, required=False)
    conversation_id = serializers.UUIDField(write_only=True, required=False)
    message_body_text = serializers.CharField(source="content", read_only=True)
    is_own_message = serializers.SerializerMethodField()
    time_since_sent = serializers.SerializerMethodField()
    formatted_sent_at = serializers.SerializerMethodField()

    class Meta:
        """Message model serializer configuration"""

        model = Message
        fields = [
            "message_id",
            "sender",
            "sender_id",
            "conversation",
            "conversation_id",
            "content",
            "message_type",
            "message_body_text",
            "timestamp",
            "is_edited",
            "edited_at",
            "is_own_message",
            "time_since_sent",
            "formatted_sent_at",
        ]
        read_only_fields = ["message_id", "timestamp", "edited_at", "conversation"]

    def get_is_own_message(self, obj):
        """Check if the message belongs to the current user."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return obj.sender == request.user
        return False

    def get_time_since_sent(self, obj):
        """Return human-readable time since message was sent."""
        now = timezone.now()
        diff = now - obj.timestamp

        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"

    def validate(self, attrs):
        """Validate message data."""
        request = self.context.get("request")

        # Set sender to current user if not provided
        if not attrs.get("sender_id") and request and hasattr(request, "user"):
            attrs["sender_id"] = request.user.user_id

        # Validate message body is not empty
        content = attrs.get("content", "").strip()
        if not content:
            raise serializers.ValidationError(
                {"content": "Message body cannot be empty."}
            )
        attrs["content"] = content

        return attrs

    def get_sender_email(self, obj):
        """Get sender's email address."""
        return obj.sender.email

    def get_formatted_sent_at(self, obj):
        """Format the timestamp timestamp for display."""
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.timestamp else None

    def create(self, validated_data):
        """Create a new message."""
        sender_id = validated_data.pop("sender_id", None)
        conversation_id = validated_data.pop("conversation_id", None)

        # pylint: disable=no-member
        if sender_id:
            try:
                sender = User.objects.get(user_id=sender_id)
                validated_data["sender"] = sender
            except User.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"sender_id": "Invalid sender ID."}
                ) from exc

        # pylint: disable=no-member
        if conversation_id:
            try:
                conversation = Conversation.objects.get(conversation_id=conversation_id)
                validated_data["conversation"] = conversation
            except Conversation.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"conversation_id": "Invalid conversation ID."}
                ) from exc

        return Message.objects.create(**validated_data)


class MessageSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for message summary in nested relationships.
    """

    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    message_preview = serializers.SerializerMethodField()

    class Meta:
        """Message Summary serializer configuration"""

        model = Message
        fields = [
            "message_id",
            "sender_name",
            "message_preview",
            "message_type",
            "timestamp",
        ]
        read_only_fields = ["message_id", "timestamp"]

    def get_message_preview(self, obj):
        """Return a truncated version of the message body."""
        if len(obj.content) > 100:
            return obj.content[:100] + "..."
        return obj.content


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer for Conversation Participants."""

    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        """ConversationParticipant model serializer configuration"""

        model = ConversationParticipant
        fields = ["user", "user_id", "joined_at"]
        read_only_fields = ["joined_at"]


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model with nested participants and messages.
    """

    participants = UserSummarySerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    messages = MessageSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        """Conversation model configuration"""

        model = Conversation
        fields = [
            "conversation_id",
            "title",
            "participants",
            "participant_ids",
            "messages",
            "latest_message",
            "participant_count",
            "unread_count",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["conversation_id", "created_at"]

    def get_latest_message(self, obj):
        """Get the most recent message in the conversation."""
        latest_message = obj.messages.order_by("-timestamp").first()
        if latest_message:
            return MessageSummarySerializer(latest_message).data
        return None

    def get_participant_count(self, obj):
        """Get the number of participants in the conversation."""
        return obj.get_participant_count()

    def get_unread_count(self, obj):
        """Get unread message count for the current user."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            # Count messages not read by current user
            unread_messages = obj.messages.exclude(
                read_status__user=request.user
            ).count()
            return unread_messages
        return 0

    def validate_participant_ids(self, value):
        """Validate that all participant IDs exist."""
        if not value:
            return value

        existing_users = User.objects.filter(user_id__in=value)
        if existing_users.count() != len(value):
            invalid_ids = set(value) - set(
                existing_users.values_list("user_id", flat=True)
            )
            raise serializers.ValidationError(f"Invalid user IDs: {list(invalid_ids)}")

        return value

    # pylint: disable=no-member
    def create(self, validated_data):
        """Create a new conversation with participants."""
        participant_ids = validated_data.pop("participant_ids", [])

        # Add current user to participants if not already included
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            current_user_id = request.user.user_id
            if current_user_id not in participant_ids:
                participant_ids.append(current_user_id)

        conversation = Conversation.objects.create(**validated_data)

        # Add participants
        if participant_ids:
            participants = User.objects.filter(user_id__in=participant_ids)
            conversation.participants.set(participants)

        return conversation

    def update(self, instance, validated_data):
        """Update conversation, handling participants separately."""
        participant_ids = validated_data.pop("participant_ids", None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update participants if provided
        if participant_ids is not None:
            participants = User.objects.filter(user_id__in=participant_ids)
            instance.participants.set(participants)

        instance.save()
        return instance


class ConversationSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for conversation summary in lists.
    """

    participant_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    other_participants = serializers.SerializerMethodField()

    class Meta:
        """ConversationSummary model configuration"""

        model = Conversation
        fields = [
            "conversation_id",
            "title",
            "participant_count",
            "latest_message",
            "other_participants",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["conversation_id", "created_at"]

    def get_participant_count(self, obj):
        """Return participant total count"""
        return obj.get_participant_count()

    def get_latest_message(self, obj):
        """Return the latest message"""
        latest_message = obj.messages.order_by("-timestamp").first()
        if latest_message:
            return {
                "content": latest_message.content[:50]
                + ("..." if len(latest_message.content) > 50 else ""),
                "sender_name": latest_message.sender.get_full_name(),
                "timestamp": latest_message.timestamp,
            }
        return None

    def get_other_participants(self, obj):
        """Get other participants excluding the current user."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            other_participants = obj.participants.exclude(user_id=request.user.user_id)
            return UserSummarySerializer(other_participants, many=True).data
        return UserSummarySerializer(obj.participants.all(), many=True).data


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for MessageReadStatus model.
    """

    user = UserSummarySerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=False)
    message_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        """MessageReadStatus model configuration"""

        model = MessageReadStatus
        fields = ["id", "message", "message_id", "user", "user_id", "read_at"]
        read_only_fields = ["id", "read_at"]

    # pylint: disable=no-member
    def create(self, validated_data):
        """Create a new read status entry."""
        user_id = validated_data.pop("user_id", None)
        message_id = validated_data.pop("message_id", None)

        # Set user to current user if not provided
        request = self.context.get("request")
        if not user_id and request and hasattr(request, "user"):
            user_id = request.user.user_id

        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
                validated_data["user"] = user
            except User.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"user_id": "Invalid user ID."}
                ) from exc

        if message_id:
            try:
                message = Message.objects.get(message_id=message_id)
                validated_data["message"] = message
            except Message.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"message_id": "Invalid message ID."}
                ) from exc

        # Create or update read status
        read_status, created = MessageReadStatus.objects.get_or_create(
            message=validated_data["message"], user=validated_data["user"]
        )

        return read_status, created


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication.
    """

    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"})

    # pylint: disable=no-member
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            # Use email to find username for authentication
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist as exc:
                raise serializers.ValidationError("Invalid email or password.") from exc

            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )

            if not user:
                raise serializers.ValidationError("Invalid email or password.")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')

    def create(self, validated_data):
        raise NotImplementedError("Create method is not used in LoginSerializer.")

    def update(self, instance, validated_data):
        raise NotImplementedError("Update method is not used in LoginSerializer.")


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """

    old_password = serializers.CharField(style={"input_type": "password"})
    new_password = serializers.CharField(
        style={"input_type": "password"}, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        """Validate password change data."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New password fields didn't match."}
            )
        return attrs

    def validate_old_password(self, value):
        """Validate old password."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            if not request.user.check_password(value):
                raise serializers.ValidationError("Incorrect old password.")
        return value

    def save(self, **kwargs):
        """Save new password."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            request.user.set_password(self.validated_data["new_password"])
            request.user.save()
            return request.user

    def create(self, validated_data):
        raise NotImplementedError(
            "Create method is not used in PasswordChangeSerializer."
        )

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "Update method is not used in PasswordChangeSerializer."
        )


class ParticipantActionSerializer(serializers.Serializer):
    """
    Serializer for participant actions in a conversation
    (e.g., add/remove participant).
    """

    user_id = serializers.UUIDField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None

    # pylint: disable=no-member
    def validate_user_id(self, value):
        """Ensure the user exists and cache it on the serializer."""
        try:
            self._user = User.objects.get(user_id=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found") from exc
        return value

    def get_user(self):
        """Return cached User instance (populated during validation)."""
        return self._user

    def create(self, validated_data):
        raise NotImplementedError(
            "Create method is not used in ParticipantActionSerializer."
        )

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "Update method is not used in ParticipantActionSerializer."
        )


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for registering new users"""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Registration serializer configuration"""

        model = User
        fields = ("user_id", "email", "password", "first_name", "last_name")

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return user


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    sender_name = serializers.CharField(
        source="message.sender.get_full_name", read_only=True
    )
    conversation_id = serializers.UUIDField(
        source="message.conversation.conversation_id", read_only=True
    )
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        """Notification serializer definition"""
        model = Notification
        fields = [
            "notification_id",
            "notification_type",
            "title",
            "message_content",
            "is_read",
            "sender_name",
            "conversation_id",
            "formatted_time",
            "created_at",
        ]
        read_only_fields = ["notification_id", "created_at"]

    def get_formatted_time(self, obj):
        """Return formatted time for display."""

        return timesince(obj.created_at) + " ago"


class NotificationSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for notification lists."""

    class Meta:
        """Notification serializer summary definition"""
        model = Notification
        fields = [
            "notification_id",
            "notification_type",
            "title",
            "is_read",
            "created_at",
        ]
