"""Module imports for messaging.serializers"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Message, Notification, MessageHistory


# pylint: disable=no-member
class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    class Meta:
        """Meta Class"""
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class RecursiveField(serializers.Serializer):
    """Return thread of messages"""
    def to_representation(self, instance):
        serializer = self.parent.parent.__class__(instance, context=self.context)
        return serializer.data

    def create(self, validated_data):
        """Not needed, since this serializer is read-only"""
        raise NotImplementedError("RecursiveField does not support creation")

    def update(self, instance, validated_data):
        """Not needed, since this serializer is read-only"""
        raise NotImplementedError("RecursiveField does not support updates")


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""

    sender_username = serializers.CharField(source="sender.username", read_only=True)
    receiver_username = serializers.CharField(
        source="receiver.username", read_only=True
    )
    sender_details = UserSerializer(source="sender", read_only=True)
    receiver_details = UserSerializer(source="receiver", read_only=True)
    replies = RecursiveField(many=True, read_only=True)

    class Meta:
        """Meta class"""
        model = Message
        fields = [
            "id",
            "sender",
            "sender_username",
            "sender_details",
            "receiver",
            "replies",
            "parent_message",
            "receiver_username",
            "receiver_details",
            "content",
            "message_type",
            "timestamp",
            "is_read",
        ]
        read_only_fields = ["id", "timestamp", "sender_username", "receiver_username"]

    def validate(self, attrs):
        """Validate that sender and receiver are different"""
        request = self.context.get("request")
        if request and request.method == "POST":
            sender = request.user
            receiver = attrs.get("receiver")
            if sender == receiver:
                raise serializers.ValidationError(
                    "You cannot send a message to yourself."
                )
        return attrs

    def create(self, validated_data):
        """Set the sender as the current user"""
        request = self.context.get("request")
        validated_data["sender"] = request.user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating messages"""

    class Meta:
        """Meta class"""
        model = Message
        fields = ["receiver", "content", "parent_message"]
        extra_kwargs = {"parent_message": {"required": False, "allow_null": True}}


    def validate(self, attrs):
        """Validate that sender and receiver are different"""
        request = self.context.get("request")
        if request:
            sender = request.user
            receiver = attrs.get("receiver")
            if sender == receiver:
                raise serializers.ValidationError(
                    "You cannot send a message to yourself."
                )
        return attrs

    def create(self, validated_data):
        """Set the sender as the current user"""
        request = self.context.get("request")
        validated_data["sender"] = request.user
        return Message.objects.create(**validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    user_username = serializers.CharField(source="user.username", read_only=True)
    message_details = MessageSerializer(source="message", read_only=True)

    class Meta:
        """Meta class"""
        model = Notification
        fields = [
            "id",
            "user",
            "user_username",
            "message",
            "message_details",
            "notification_type",
            "content",
            "timestamp",
            "is_read",
        ]
        read_only_fields = [
            "id",
            "user",
            "message",
            "notification_type",
            "content",
            "timestamp",
            "user_username",
        ]


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification read status"""

    class Meta:
        """Meta class"""
        model = Notification
        fields = ["is_read"]


class ConversationSerializer(serializers.Serializer):
    """Serializer for conversation between two users"""

    other_user = UserSerializer()
    last_message = MessageSerializer()
    unread_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()

    def create(self, validated_data):
        """Not needed, since this serializer is read-only"""
        raise NotImplementedError("ConversationSerializer does not support creation")

    def update(self, instance, validated_data):
        """Not needed, since this serializer is read-only"""
        raise NotImplementedError("ConversationSerializer does not support updates")


class MessageHistorySerializer(serializers.ModelSerializer):
    """Serializer for message history"""

    class Meta:
        """Meta class"""
        model = MessageHistory
        fields = ["old_content", "edited_at"]
