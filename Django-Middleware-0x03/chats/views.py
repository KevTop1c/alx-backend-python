"""Imports for ViewSet"""

from django.db.models import Q
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import User, Conversation, Message, MessageReadStatus
from .filters import MessageFilter
from .pagination import MessagePagination
from .permissions import CanManageMessage
from .serializers import (
    UserSerializer,
    UserSummarySerializer,
    ConversationSerializer,
    ConversationSummarySerializer,
    MessageSerializer,
    MessageReadStatusSerializer,
    ParticipantActionSerializer,
    RegisterSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for consistent pagination across viewsets.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["role", "is_active"]
    ordering_fields = ["created_at", "first_name", "last_name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Use summary serializer for list view."""
        if self.action == "list":
            return UserSummarySerializer
        return UserSerializer

    # pylint: disable=no-member
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            return User.objects.all()
        else:
            # Regular users can only see users in their conversations
            return User.objects.filter(
                Q(conversations__participants=user) | Q(user_id=user.user_id)
            ).distinct()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["put", "patch"])
    def update_profile(self, request):
        """Update current user profile."""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# pylint: disable=no-member
class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    Provides CRUD operations and additional conversation-specific actions.
    """

    serializer_class = ConversationSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title"]
    filterset_fields = ["is_active"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return conversations where the user is a participant."""
        return (
            Conversation.objects.filter(participants=self.request.user, is_active=True)
            .prefetch_related("participants")
            .distinct()
        )

    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action == "list":
            return ConversationSummarySerializer
        return ConversationSerializer

    def get_serializer_context(self):
        """Add request context for serializers."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        """Automatically add current user as participant when creating conversation."""
        conversation = serializer.save()
        conversation.participants.add(self.request.user)

    @action(detail=True, methods=["post"])
    def add_participant(self, request, _pk=None):
        """
        Add a participant to the conversation.
        Expected payload: {"user_id": "uuid"}
        """
        conversation = self.get_object()

        # Check if current user has permission to add participants
        if not conversation.can_add_participants(request.user):
            return Response(
                {
                    "error": "You don't have permission to add participants to this conversation"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ParticipantActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.get_user()
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is already a participant
        if conversation.participants.filter(id=user.user_id).exists():
            return Response(
                {"message": f"{user.get_full_name()} is already in the conversation"},
                status=status.HTTP_200_OK,
            )

        try:
            conversation.add_participant(user)
            return Response(
                {"message": f"{user.get_full_name()} added to conversation"},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"error": e.message_dict if hasattr(e, "message_dict") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError as e:
            if "unique constraint" in str(e).lower():
                return Response(
                    {"error": "User is already a participant in this conversation"},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"error": "Database error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def remove_participant(self, request, _pk=None):
        """
        Remove a participant from the conversation.
        Expected payload: {"user_id": "uuid"}
        """
        conversation = self.get_object()
        serializer = ParticipantActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.get_user()

        # Don't allow removing the last participant
        if conversation.get_participant_count() <= 1:
            return Response(
                {"error": "Cannot remove the last participant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation.remove_participant(user)
        return Response(
            {"message": f"{user.get_full_name()} removed from conversation"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def leave_conversation(self, request, _pk=None):
        """
        Allow current user to leave the conversation.
        """
        conversation = self.get_object()

        # Don't allow leaving if user is the only participant
        if conversation.get_participant_count() <= 1:
            conversation.is_active = False
            conversation.save()
            return Response(
                {"message": "Conversation deactivated"}, status=status.HTTP_200_OK
            )

        conversation.remove_participant(request.user)
        return Response(
            {"message": "You have left the conversation"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, _pk=None):
        """
        Mark all messages in conversation as read by current user.
        """
        conversation = self.get_object()
        user = request.user

        # Get unread messages
        unread_messages = conversation.messages.exclude(read_status__user=user)

        # Create read status for unread messages
        read_statuses = [
            MessageReadStatus(message=message, user=user) for message in unread_messages
        ]

        MessageReadStatus.objects.bulk_create(read_statuses, ignore_conflicts=True)

        return Response(
            {"message": f"Marked {len(read_statuses)} messages as read"},
            status=status.HTTP_200_OK,
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages within conversations (nested routing).
    Provides CRUD operations and message-specific actions.
    """

    serializer_class = MessageSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, CanManageMessage]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["message_body"]
    filterset_fields = ["message_type", "is_edited"]
    filterset_class = MessageFilter
    pagination_class = MessagePagination
    ordering_fields = ["sent_at"]
    ordering = ["-sent_at"]

    def get_queryset(self):
        """Return messages from the specific conversation where user is a participant."""
        conversation_id = self.kwargs.get("conversation_pk")

        if not conversation_id:
            return Message.objects.none()

        return (
            Message.objects.filter(
                conversation__conversation_id=conversation_id,
                conversation__participants=self.request.user,
                conversation__is_active=True,
            )
            .select_related("sender", "conversation")
            .order_by("-sent_at")
        )

    def get_serializer_context(self):
        """Add request context for serializers."""
        context = super().get_serializer_context()
        context["request"] = self.request
        context["conversation_id"] = self.kwargs.get("conversation_pk")
        return context

    def perform_create(self, serializer):
        """Automatically set conversation and sender when creating message."""
        conversation_id = self.kwargs.get("conversation_pk")
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        if not conversation_id:
            raise ValidationError({"conversation": "Conversation ID is required."})

        # Verify user is a participant in the conversation
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist as exc:
            raise NotFound("Conversation not found") from exc

        if not conversation.participants.filter(id=self.request.user.user_id).exists():
            raise PermissionDenied("You are not a participant in this conversation")

        serializer.save(conversation=conversation, sender=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Update a message (only sender can edit their own messages).
        """
        message = self.get_object()

        # Only allow sender to edit their own message
        if message.sender != request.user:
            return Response(
                {"error": "You can only edit your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only allow editing message body and type
        allowed_fields = ["message_body", "message_type"]
        filtered_data = {
            key: value for key, value in request.data.items() if key in allowed_fields
        }

        serializer = self.get_serializer(message, data=filtered_data, partial=True)

        if serializer.is_valid():
            # Mark message as edited
            message = serializer.save()
            message.mark_as_edited()

            response_serializer = MessageSerializer(
                message, context=self.get_serializer_context()
            )
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (only sender can delete their own messages).
        """
        message = self.get_object()

        # Only allow sender to delete their own message
        if message.sender != request.user:
            return Response(
                {"error": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, *_args, **_kwarags):
        """
        Mark a specific message as read by current user.
        """
        message = self.get_object()
        user = request.user

        _, created = MessageReadStatus.objects.get_or_create(message=message, user=user)

        if created:
            return Response(
                {"message": "Message marked as read"}, status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {"message": "Message already read"}, status=status.HTTP_200_OK
            )


# Additional ViewSet for message read status management
class MessageReadStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing message read statuses.
    Read-only operations only.
    """

    serializer_class = MessageReadStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    # pylint: disable=no-member
    def get_queryset(self):
        """Return read statuses for messages in user's conversations."""
        return MessageReadStatus.objects.filter(
            message__conversation__participants=self.request.user
        ).select_related("user", "message")

    @action(detail=False, methods=["get"])
    def by_message(self, request):
        """
        Get read statuses for a specific message.
        Query parameter: message_id
        """
        message_id = request.query_params.get("message_id")
        if not message_id:
            return Response(
                {"error": "message_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            message = Message.objects.get(message_id=message_id)
            # Verify user has access to this message
            if not message.conversation.participants.filter(
                user_id=request.user.user_id
            ).exists():
                return Response(
                    {"error": "You do not have access to this message"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            read_statuses = self.get_queryset().filter(message=message)
            serializer = self.get_serializer(read_statuses, many=True)
            return Response(serializer.data)

        except Message.DoesNotExist:
            return Response(
                {"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND
            )


class FlatMessageViewSet(viewsets.ModelViewSet):
    """
    Flat ViewSet for messages across all conversations (non-nested).
    Useful for search and global message operations.
    """

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["message_body"]
    filterset_class = MessageFilter
    pagination_class = MessagePagination

    def get_queryset(self):
        """Return messages from all conversations where user is a participant."""
        return Message.objects.filter(
            conversation__participants=self.request.user, conversation__is_active=True
        ).select_related("sender", "conversation")

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Search messages across all user's conversations.
        Query parameter: q (search term)
        """
        query = request.query_params.get("q", "")
        if not query:
            return Response(
                {"error": 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        messages = self.get_queryset().filter(message_body__icontains=query)

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(
            messages, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """
        Get all unread messages for the current user.
        """
        user = request.user
        unread_messages = (
            self.get_queryset()
            .exclude(read_status__user=user)
            .exclude(sender=user)  # Exclude user's own messages
        )

        page = self.paginate_queryset(unread_messages)
        if page is not None:
            serializer = MessageSerializer(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(
            unread_messages, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)


class RegistrationView(generics.CreateAPIView):
    """
    API endpoint to register a new user.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User registered successfully",
                "user": serializer.data,
                "user_id": user.user_id,
            },
            status=status.HTTP_201_CREATED,
        )


@csrf_exempt
def test_chat_endpoint(request):
    """Test endpoint for rate limiting middleware"""
    if request.method == "POST":
        return JsonResponse(
            {"status": "Message received", "message": request.POST.get("message", "")}
        )
    return JsonResponse({"error": "POST required"})
