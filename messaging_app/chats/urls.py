"""Imports for chats/urls.py"""

from django.urls import path, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from .views import ConversationViewSet, MessageViewSet, MessageReadStatusViewSet
from .auth import register, login_view, logout_view, change_password, verify_token

# Main router
router = routers.DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

# Nested router for messages under conversations
conversations_router = nested_routers.NestedDefaultRouter(
    router, r"conversations", lookup="conversation"
)
conversations_router.register(
    r"messages", MessageViewSet, basename="conversation-messages"
)
conversations_router.register(
    r"read-status", MessageReadStatusViewSet, basename="messagereadstatus"
)

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/logout/", logout_view, name="logout"),
    path("auth/change-password/", change_password, name="change-password"),
    path("auth/verify-token/", verify_token, name="verify-token"),
    # All other router urls
    path("", include(router.urls)),
    path("", include(conversations_router.urls)),
]
