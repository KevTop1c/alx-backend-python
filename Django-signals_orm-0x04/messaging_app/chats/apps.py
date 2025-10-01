"""Module import for signal registration"""

from django.apps import AppConfig


class ChatsConfig(AppConfig):
    """Signal registration"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chats"

    def ready(self):
        """Import and register signals when app is ready."""
        import chats.signals
