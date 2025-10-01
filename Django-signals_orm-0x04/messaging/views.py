from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q
from django.contrib.auth.models import User
from .models import Message, Notification
from .serializers import (
    MessageSerializer,
    MessageCreateSerializer,
    NotificationSerializer,
    NotificationUpdateSerializer,
    UserSerializer,
)


# pylint: disable=no-member
# pylint: disable=unused-argument
class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["content", "sender__username", "receiver__username"]
    ordering_fields = ["timestamp", "is_read"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        """Return messages where user is sender or receiver"""
        user = self.request.user
        return Message.objects.filter(Q(sender=user) | Q(receiver=user)).select_related(
            "sender", "receiver"
        )

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """Automatically set sender to current user"""
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=["get"])
    def sent(self, request):
        """Get all messages sent by the current user"""
        messages = (
            Message.objects.filter(sender=request.user)
            .select_related("sender", "receiver")
            .order_by("-timestamp")
        )

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def received(self, request):
        """Get all messages received by the current user"""
        messages = (
            Message.objects.filter(receiver=request.user)
            .select_related("sender", "receiver")
            .order_by("-timestamp")
        )

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """Get all unread messages for the current user"""
        messages = (
            Message.objects.filter(receiver=request.user, is_read=False)
            .select_related("sender", "receiver")
            .order_by("-timestamp")
        )

        serializer = self.get_serializer(messages, many=True)
        return Response({"count": messages.count(), "messages": serializer.data})

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a specific message as read"""
        message = self.get_object()

        # Only the receiver can mark a message as read
        if message.receiver != request.user:
            return Response(
                {"error": "You can only mark your own received messages as read."},
                status=status.HTTP_403_FORBIDDEN,
            )

        message.is_read = True
        message.save()

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="conversation/(?P<user_id>[0-9]+)")
    def conversation(self, request, user_id=None):
        """Get conversation between current user and another user"""
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        messages = (
            Message.objects.filter(
                Q(sender=request.user, receiver=other_user)
                | Q(sender=other_user, receiver=request.user)
            )
            .select_related("sender", "receiver")
            .order_by("-timestamp")
        )

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def conversations(self, request):
        """Get list of all conversations with message counts"""
        user = request.user

        # Get all users the current user has exchanged messages with
        sent_to = Message.objects.filter(sender=user).values_list("receiver", flat=True)
        received_from = Message.objects.filter(receiver=user).values_list(
            "sender", flat=True
        )
        conversation_user_ids = set(list(sent_to) + list(received_from))

        conversations = []
        for user_id in conversation_user_ids:
            other_user = User.objects.get(id=user_id)

            # Get last message in conversation
            last_message = (
                Message.objects.filter(
                    Q(sender=user, receiver=other_user)
                    | Q(sender=other_user, receiver=user)
                )
                .select_related("sender", "receiver")
                .order_by("-timestamp")
                .first()
            )

            # Count unread messages from this user
            unread_count = Message.objects.filter(
                sender=other_user, receiver=user, is_read=False
            ).count()

            conversations.append(
                {
                    "other_user": UserSerializer(other_user).data,
                    "last_message": (
                        MessageSerializer(last_message).data if last_message else None
                    ),
                    "unread_count": unread_count,
                    "timestamp": last_message.timestamp if last_message else None,
                }
            )

        # Sort by timestamp (most recent first)
        conversations.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        return Response(conversations)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["timestamp", "is_read"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        """Return only notifications for the current user"""
        return Notification.objects.filter(user=self.request.user).select_related(
            "user", "message", "message__sender"
        )

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ["update", "partial_update"]:
            return NotificationUpdateSerializer
        return NotificationSerializer

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """Get all unread notifications"""
        notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(
            {"count": notifications.count(), "notifications": serializer.data}
        )

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)

        return Response(
            {
                "message": f"{updated_count} notifications marked as read.",
                "count": updated_count,
            }
        )

    @action(detail=False, methods=["delete"])
    def delete_all_read(self, request):
        """Delete all read notifications"""
        deleted_count, _ = self.get_queryset().filter(is_read=True).delete()

        return Response(
            {
                "message": f"{deleted_count} read notifications deleted.",
                "count": deleted_count,
            }
        )


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing users (read-only).
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "email", "first_name", "last_name"]

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete_user(self, request):
        user = request.user
        user.delete()
        return Response(
            {"detail": "User account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
