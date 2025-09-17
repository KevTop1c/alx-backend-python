from rest_framework import serializers
from .models import User, Conversation, ConversationParticipant, Message


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with password handling and validation.
    """

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
        ]
        read_only_fields = ["user_id", "created_at"]
        extra_kwargs = {"email": {"required": True}}

    def create(self, validated_data):
        """Create a new user with encrypted password"""
        password = validated_data.pop("password", None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model with sender details."""

    sender = UserSerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True)
    message_body_text = serializers.CharField(source="message_body", read_only=True)
    sender_email = serializers.SerializerMethodField()
    formatted_sent_at = serializers.SerializerMethodField()

    class Meta:
        """Message model serializer configuration"""

        model = Message
        fields = [
            "message_id",
            "sender",
            "sender_id",
            "conversation",
            "message_body",
            "message_body_text",
            "formatted_sent_at"
            "sent_at",
        ]
        read_only_fields = ["message_id", "sent_at"]

    def get_sender_email(self, obj):
        """Get sender's email address."""
        return obj.sender.email

    def get_formatted_sent_at(self, obj):
        """Format the sent_at timestamp for display."""
        return obj.sent_at.strftime('%Y-%m-%d %H:%M:%S') if obj.sent_at else None

    def create(self, validated_data):
        """Create a message and validate sender is conversation participant."""
        sender_id = validated_data.pop("sender_id")
        conversation = validated_data["conversation"]

        # Verify user is a participant in the conversation
        if not conversation.participants.filter(user_id=sender_id).exists():
            raise serializers.ValidationError(
                "Sender must be a participant of the conversation"
            )

        sender = User.objects.get(user_id=sender_id)
        validated_data["sender"] = sender

        # pylint: disable=no-member
        return Message.objects.create(**validated_data)


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
    """Serializer for Conversation model with nested participants and messages."""

    participants = ConversationParticipantSerializer(
        source="conversationparticipant_set", many=True, read_only=True
    )
    messages = MessageSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        """Conversation model serializer configuration"""

        model: Conversation
        fields = [
            "conversation_id",
            "participants",
            "participant_ids",
            "messages",
            "created_at",
        ]
        read_only_fields = ["conversation_id", "created_at"]

    def create(self, validated_data):
        """Create conversation and add participants."""
        participant_ids = validated_data.pop("participant_ids", [])

        # Create conversation without participant first
        # pylint: disable=no-member
        conversation = Conversation.objects.create()

        # Add participants
        for user_id in participant_ids:
            try:
                user = User.objects.get(user_id=user_id)
                ConversationParticipant.objects.create(
                    conversation=conversation, user=user
                )
            except User.DoesNotExist as exc:
                raise serializers.ValidationError(
                    f"User with ID {user_id} does not exist"
                ) from exc
        return conversation
