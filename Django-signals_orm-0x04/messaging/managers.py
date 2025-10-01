"""Module imports for customer managers"""
from django.db import models


class UnreadMessagesManager(models.Manager):
    """
    Manager to return unread messages for a specific user.
    Exposes unread_for_user(user) for use in views.
    """

    def unread_for_user(self, user):
        """Return a queryset for unread messages for user"""
        return (
            self.get_queryset()
            .filter(receiver=user, is_read=False)
            .select_related("sender", "receiver")
        )
