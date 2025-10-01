from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Message, Notification, MessageHistory


# pylint: disable=unused-argument
# pylint: disable=no-member
@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal handler that creates a notification when a new message is sent.
    """
    if created:
        # Only create notification for new messages, not updates
        notification_content = (
            f"New message from {instance.sender.username}: {instance.content[:50]}"
        )

        # Add ellipsis if content was truncated
        if len(instance.content) > 50:
            notification_content += "..."

        Notification.objects.create(
            user=instance.receiver,
            message=instance,
            notification_type="message",
            content=notification_content,
        )

        # Optional: Log the notification creation
        print(f"Notification created for {instance.receiver.username}")


@receiver(pre_save, sender=Message)
def log_message_edit(sender, instance, **kwargs):
    """
    Signal handler that logs messages.
    """
    if not instance.pk:
        # New message being created (skip logging)
        return

    try:
        old_message = Message.objects.get(pk=instance.pk)
    except Message.DoesNotExist:
        return

    if old_message.content != instance.content:
        # Save old content to history
        MessageHistory.objects.create(
            message=old_message, old_content=old_message.content
        )
        # Mark the message as edited
        instance.edited = True
