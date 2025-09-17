"""Imports for ViewSet"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from .models import Conversation, Message, ConversationParticipant
from .serializers import ConversationSerializer, MessageSerializer


# Create your views here.
class ConversationViewSet(viewsets.ModelViewSet):
    """API endpoint for managing conversations"""

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["created_at"]

    def get_queryset(self):
        """Return conversations where the current user is a participant with optional filtering."""

        # pylint: disable=no-member
        queryset = Conversation.objects.filter(
            participants__user=self.request.user
        ).distinct()

        # Additional filtering based on query parameters
        created_after = self.request.query_params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)

        has_messages = self.request.query_params.get("has_messages")
        if has_messages:
            if has_messages.lower() == "true":
                queryset = queryset.filter(messages__isnull=False)
            elif has_messages.lower() == "false":
                queryset = queryset.filter(messages__isnull=True)

        return queryset

    def perform_create(self, serializer):
        """Create conversation and add current user a participant."""
        with transaction.atomic():
            conversation = serializer.save()

            # Add current user to participants
            # pylint: disable=no-member
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=self.request.user,
            )

    def create(self, request, *args, **kwargs):
        """Create new conversation with participants."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure current user is included in participants
        participant_ids = request.data.get("participant_ids", [])
        if str(self.request.user.user_id) not in participant_ids:
            participant_ids.append(str(self.request.user.user_id))

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(detail=True, methods=["post"])
    def send_message(self, request):
        """Send a message to this conversation."""
        conversation = self.get_object()

        # Verify user is a participant
        if not conversation.participants.filter(user=request.user).exists():
            return Response(
                {"error": "You are not a participant in this conversation"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create message
        # pylint: disable=no-member
        message = Message.objects.create(
            sender=request.user,
            conversation=conversation,
            message_body=request.data.get("message_body", ""),
        )

        response_serializer = MessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def messages(self):
        """Get all messages in a specific conversation."""
        conversation = self.get_object()
        messages = conversation.messages.select_related("sender").order_by("sent_at")
        page = self.paginate_queryset(messages)

        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing messages.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["conversation", "sent_at", "sender"]

    def get_queryset(self):
        """Return messages in conversations where user is a participant with filtering."""

        # pylint: disable=no-member
        queryset = Message.objects.filter(
            conversation__participants__user=self.request.user
        ).select_related("sender", "conversation")

        # Additional filtering based on query parameters
        conversation_id = self.request.query_params.get("conversation")
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        sender_id = self.request.query_params.get("sender")
        if sender_id:
            queryset = queryset.filter(sender_id=sender_id)

        sent_after = self.request.query_params.get("sent_after")
        if sent_after:
            queryset = queryset.filter(sent_at__gte=sent_after)

        sent_before = self.request.query_params.get("sent_before")
        if sent_before:
            queryset = queryset.filter(sent_at__lte=sent_before)

        return queryset.order_by("-sent_at")

    def perform_create(self, serializer):
        """Set sender to current user and validate conversation participation."""
        conversation = serializer.validated_data["conversation"]

        # Verify user is a participant in the conversation
        if not conversation.participants.filter(user=self.request.user).exists():
            raise serializer.ValidationError(
                "You are not a participant in this conversation"
            )

        serializer.save(sender=self.request.user)
