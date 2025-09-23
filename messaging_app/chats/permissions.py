"""Module import for permissions"""

from rest_framework import permissions
from .models import UserRole, Conversation, Message


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the owner
        if hasattr(obj, "sender"):
            return obj.sender == request.user
        elif hasattr(obj, "user"):
            return obj.user == request.user

        return False


class IsConversationParticipant(permissions.BasePermission):
    """
    Permission to check if user is a participant in the conversation.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Conversation):
            return obj.participants.filter(user_id=request.user.user_id).exists()
        elif isinstance(obj, Message):
            return obj.conversation.participants.filter(
                user_id=request.user.user_id
            ).exists()

        return False


class IsMessageSender(permissions.BasePermission):
    """
    Permission to check if user is the sender of the message.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Message):
            return obj.sender == request.user
        return False


class CanManageConversation(permissions.BasePermission):
    """
    Permission for conversation management actions.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Conversation):
            # Check if user is participant
            is_participant = obj.participants.filter(
                user_id=request.user.user_id
            ).exists()

            # For certain actions, might need admin/host role
            if view.action in ["add_participant", "remove_participant"]:
                return is_participant and (
                    request.user.role in [UserRole.ADMIN, UserRole.HOST]
                    or obj.participants.count() <= 2  # Allow in small conversations
                )

            return is_participant

        return False
