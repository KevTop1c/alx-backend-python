"""Imports for chats/urls.py"""

from django.urls import path, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

# from .views import (
#     ConversationViewSet,
#     MessageViewSet,
#     MessageReadStatusViewSet,
#     FlatMessageViewSet,
#     RegistrationView,
#     test_chat_endpoint,
#     admin_dashboard,
#     system_settings,
#     moderation_reports,
#     user_management,
#     public_data,
#     test_login,
# )
# from . import auth
# from .auth import register, login_view, logout_view, change_password, verify_token

# Main router
router = routers.DefaultRouter()
router.register(r"conversations", views.ConversationViewSet, basename="conversation")
router.register(r"messages", views.FlatMessageViewSet, basename="flat-messages")

# Nested router for messages under conversations
conversations_router = nested_routers.NestedSimpleRouter(
    router, r"conversations", lookup="conversation"
)
conversations_router.register(
    r"messages", views.MessageViewSet, basename="conversation-messages"
)
conversations_router.register(
    r"read-status", views.MessageReadStatusViewSet, basename="messagereadstatus"
)

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", views.RegistrationView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/verify-token/", TokenRefreshView.as_view(), name="verify-token"),
    # path("auth/register/", auth.register, name="register"),
    # path("auth/login/", auth.login_view, name="login"),
    # path("auth/logout/", auth.logout_view, name="logout"),
    # path("auth/change-password/", auth.change_password, name="change-password"),
    # path("auth/verify-token/", auth.verify_token, name="verify-token"),
    # All other router urls
    path("api/", include(router.urls)),
    path("api/", include(conversations_router.urls)),
]
