"""Module import for signals"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import Message, Notification, ConversationParticipant


# pylint: disable=no-member
@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Create notifications for all participants when a new message is sent.
    Excludes the sender of the message.
    """
    if created:
        try:
            # Get all participants except the sender
            receivers = instance.conversation.participants.exclude(
                id=instance.sender.id
            )

            for user in receivers:
                # Create notification for each receiver
                Notification.objects.create(
                    user=user,
                    message=instance,
                    notification_type="new_message",
                    title=f"New message from {instance.sender.get_full_name()}",
                    message_content=(
                        instance.message_body[:100] + "..."
                        if len(instance.message_body) > 100
                        else instance.message_body
                    ),
                )

        except ObjectDoesNotExist:
            # Handle case where conversation or participants don't exist
            pass


@receiver(post_save, sender=ConversationParticipant)
def create_participant_notification(sender, instance, created, **kwargs):
    """
    Create notifications when a user joins a conversation.
    """
    if created:
        try:
            # Notify all existing participants about the new user
            existing_participants = instance.conversation.participants.exclude(
                id=instance.user.id
            )

            for participant in existing_participants:
                Notification.objects.create(
                    user=participant,
                    notification_type="user_joined",
                    title="New participant joined",
                    message_content=f"{instance.user.get_full_name()} joined the conversation",
                )

        except ObjectDoesNotExist:
            pass
