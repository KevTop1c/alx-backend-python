"""Imports for ViewSet"""

from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import User, Conversation, Message, MessageReadStatus
from .serializers import (
    UserSerializer,
    UserSummarySerializer,
    ConversationSerializer,
    ConversationSummarySerializer,
    MessageSerializer,
    MessageReadStatusSerializer,
    ParticipantActionSerializer,
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

    # pylint: disable=no-member
    def get_queryset(self):
        """Return conversations where the user is a participant."""
        return (
            Conversation.objects.filter(participants=self.request.user, is_active=True)
            .prefetch_related(
                "participants",
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender").order_by(
                        "-sent_at"
                    )[:10],
                ),
            )
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

    def create(self, request, *args, **kwargs):
        """
        Create a new conversation.
        Automatically adds the current user as a participant.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            conversation = serializer.save()

            # Return the created conversation with full details
            response_serializer = ConversationSerializer(
                conversation, context=self.get_serializer_context()
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific conversation with all messages.
        """
        conversation = self.get_object()
        serializer = ConversationSerializer(
            conversation, context=self.get_serializer_context()
        )
        return Response(serializer.data)

    # pylint: disable=no-member
    @action(detail=True, methods=["post"])
    def add_participant(self, request):
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
        if conversation.participants.filter(id=user.id).exists():
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
                {"error": e.message_dict if hasattr(e, 'message_dict') else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Database-related exceptions
        except IntegrityError as e:
            if 'unique constraint' in str(e).lower():
                return Response(
                    {"error": "User is already a participant in this conversation"},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"error": "Database error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def remove_participant(self, request):
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
    def leave_conversation(self, request):
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

    @action(detail=True, methods=["get"])
    def messages(self):
        """
        Get all messages for a conversation with pagination.
        """
        conversation = self.get_object()
        messages = conversation.messages.select_related("sender").order_by("-sent_at")

        # Apply pagination
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

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request):
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
    ViewSet for managing messages.
    Provides CRUD operations and message-specific actions.
    """

    serializer_class = MessageSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["message_body"]
    filterset_fields = ["message_type", "is_edited"]
    ordering_fields = ["sent_at"]
    ordering = ["-sent_at"]

    # pylint: disable=no-member
    def get_queryset(self):
        """Return messages from conversations where user is a participant."""
        user = self.request.user
        conversation_id = self.request.query_params.get("conversation")

        queryset = Message.objects.filter(
            conversation__participants=user
        ).select_related("sender", "conversation")

        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)

        return queryset

    def get_serializer_context(self):
        """Add request context for serializers."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """
        Send a new message to a conversation.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()

            # Return the created message with full details
            response_serializer = MessageSerializer(
                message, context=self.get_serializer_context()
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

    # pylint: disable=no-member
    @action(detail=True, methods=["post"])
    def mark_as_read(self, request):
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
