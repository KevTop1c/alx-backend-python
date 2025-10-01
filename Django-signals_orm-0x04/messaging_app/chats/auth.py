"""Module imports for JWT Authentication views"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import login, logout

from .serializers import UserSerializer, LoginSerializer, PasswordChangeSerializer


def get_safe_user_data(user):
    """Return user data without password."""
    data = UserSerializer(user).data
    data.pop("password", None)
    return data


def get_tokens_for_user(user):
    """Generate new JWT access & refresh tokens."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    """Register a new user account."""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        tokens = get_tokens_for_user(user)
        user_data = get_safe_user_data(user)

        return Response(
            {
                "user": user_data,
                "tokens": tokens,
                "message": "User created successfully",
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """Authenticate user and return JWT tokens."""
    serializer = LoginSerializer(data=request.data, context={"request": request})

    if serializer.is_valid():
        user = serializer.validated_data["user"]

        tokens = get_tokens_for_user(user)
        login(request, user)  # optional session login

        return Response(
            {
                "user": get_safe_user_data(user),
                "tokens": tokens,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Logout user by blacklisting refresh token."""
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()
    except (TokenError, InvalidToken):
        return Response(
            {"error": "Invalid refresh token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logout(request)  # optional session logout
    return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change user password and issue new tokens."""
    serializer = PasswordChangeSerializer(
        data=request.data, context={"request": request}
    )

    if serializer.is_valid():
        serializer.save()

        # Invalidate old tokens by forcing rotation
        tokens = get_tokens_for_user(request.user)

        return Response(
            {"message": "Password changed successfully", "tokens": tokens},
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def verify_token(request):
    """Verify JWT is valid and return user info."""
    return Response(
        {"user": get_safe_user_data(request.user), "message": "Token is valid"},
        status=status.HTTP_200_OK,
    )
