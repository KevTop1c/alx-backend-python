from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message, Notification


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
