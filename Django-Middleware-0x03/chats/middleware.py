"""Module imports for middleware"""

import datetime
import os
import logging
import time
import re

from collections import defaultdict
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse


# Set up logger
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Custom logging middleware"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.setup_logging()

    def setup_logging(self):
        """Setup logging directory and file"""
        try:
            self.log_dir = os.path.join(settings.BASE_DIR, "logs")
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

            self.log_file = os.path.join(self.log_dir, "requests.log")

            # Tests if we can write to the file
            with open(self.log_file, "a", encoding="utf-8"):
                pass

        except (OSError, PermissionError) as e:
            logger.error("Failed to setup logging: %s", e)

    def __call__(self, request):
        try:
            user = self.get_user_from_request(request)
            if hasattr(request, "user") and request.user.is_authenticated:
                user = request.user.username
            elif hasattr(request, "user") and request.user.username:
                user = request.user.username

            # Create log entry
            log_entry = (
                f"{datetime.datetime.now()} - User: {user} - Path {request.path}\n"
            )

            # Write to log file
            with open(self.log_file, "a", encoding="utf-8") as file:
                file.write(log_entry)

        except (OSError, PermissionError) as e:
            logger.error("Requesting logging file failed: %s", e)

        # Process the request
        response = self.get_response(request)

        return response

    def get_user_from_request(self, request):
        """Safely extract user information from request"""
        # Check if request has user attribute
        if not hasattr(request, "user"):
            return "NoUserAttribute"

        # Check if user is authenticated
        if hasattr(request.user, "is_authenticated"):
            if request.user.is_authenticated:
                return request.user.username or "AuthenticatedNoUsername"

        # Check if it's an anonymous user
        if hasattr(request.user, "username") and request.user.username:
            return request.user.username

        # Final fallbacks
        if str(request.user) != "AnonymousUser":
            return str(request.user)

        return "Anonymous"


class RestrictAccessByTimeMiddleware:
    """Custom access restriction middleware"""

    def __init__(self, get_response):
        self.get_response = get_response
        # Configurable restricted hours: 9PM (21:00) and 6AM (6:00)
        self.start_restriction = datetime.time(21, 0)
        self.end_restriction = datetime.time(6, 0)

    def __call__(self, request, *args, **kwds):
        # Get current server time
        current_time = datetime.datetime.now().time()

        # Check if current time is within restricted hours (9PM and 6PM)
        if self.is_restricted_time(current_time):
            return HttpResponseForbidden(
                f"Access denied: The messaging service is available between "
                f"6:00 AM and 9:00 PM. Current time: {current_time.strftime("%I:%M %p")}"
            )

        # If outside restricted time, process normally
        response = self.get_response(request)
        return response

    def is_restricted_time(self, current_time):
        """
        Check if current time is within restricted hours (9 PM to 6 AM)
        """
        return (current_time >= self.start_restriction) or (
            current_time <= self.end_restriction
        )


class OffensiveLanguageMiddleware:
    """
    Middleware that limits chat messages to 5 per minute per IP address
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_history = defaultdict(list)
        self.message_limit = 5
        self.time_window = 60

    def __call__(self, request):
        if self.is_chat_message_request(request):
            client_ip = self.get_client_ip(request)
            current_time = time.time()

            self.cleanup_old_requests(client_ip, current_time)
            current_count = len(self.request_history.get(client_ip, []))

            logger.info(
                "IP %s - %d/%d messages in current window",
                client_ip,
                current_count,
                self.message_limit,
            )

            if self.is_rate_limit_exceeded(client_ip):
                logger.warning("Rate limit exceeded for IP %s", client_ip)
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.message_limit} messages per minute allowed.",
                        "limit": self.message_limit,
                        "window_seconds": self.time_window,
                    },
                    status=429,
                )

            self.request_history[client_ip].append(current_time)
            logger.info(
                "Message allowed for IP %s. Count %d", client_ip, current_count + 1
            )

        response = self.get_response(request)
        return response

    def is_chat_message_request(self, request):
        """Check if request should be rate limited"""

        chat_keywords = ["chat", "message"]
        return request.method == "POST" and any(
            keyword in request.path.lower() for keyword in chat_keywords
        )

    def get_client_ip(self, request):
        """Get client IP address"""

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip

    def cleanup_old_requests(self, ip_address, current_time):
        """Remove old requests outside time window"""

        if ip_address in self.request_history:
            self.request_history[ip_address] = [
                ts
                for ts in self.request_history[ip_address]
                if current_time - ts < self.time_window
            ]

    def is_rate_limit_exceeded(self, ip_address):
        """Check if rate limit is exceeded"""
        return len(self.request_history.get(ip_address, [])) >= self.message_limit


class RolepermissionMiddleware:
    """
    Middleware that checks user's role before allowing access to specific actions
    Allows access only to admin and moderator roles for protected endpoints
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Define protected endpoints and required roles
        self.protected_endpoints = [
            (r"^/api/admin/.*", ["admin", "moderator"]),
            (r"^/api/users/.*", ["admin"]),
            (r"^/api/moderation/.*", ["admin", "moderator"]),
            (r"^/api/settings/.*", ["admin"]),
            (r"^/api/reports/.*", ["admin", "moderator"]),
            (r"^/admin/.*", ["admin"]),
            (r"^/api/delete/.*", ["admin", "moderator"]),
            (r"^/api/ban/.*", ["admin", "moderator"]),
        ]

    def __call__(self, request):
        required_roles = self.get_required_roles(request.path)

        if required_roles:
            return self.check_permission(request, required_roles)

        response = self.get_response(request)
        return response

    def get_required_roles(self, path):
        """Check if path matches any protected pattern and return required roles"""

        for pattern, roles in self.protected_endpoints:
            if re.match(pattern, path):
                return roles
        return None

    def check_permission(self, request, required_roles):
        """Check if user has permission to access the resource"""

        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "error": "Authentication required",
                    "message": "Please log in to access this resource",
                },
                status=403,
            )

        # Check role permission
        if not self.has_required_role(request.user, required_roles):
            user_role = getattr(request.user, "role", "No role assigned")
            return JsonResponse(
                {
                    "error": "Insufficient permissions",
                    "message": f"Access denied. Required roles: {', '.join(required_roles)}",
                    "your_role": user_role,
                },
                status=403,
            )

        # Permission granted, continue with request
        response = self.get_response(request)
        return response

    def has_required_role(self, user, required_roles):
        """
        Check if user has any of the required roles
        Supports multiple role checking methods
        """
        # Convert required roles to lowercase for comparison
        required_roles_lower = [role.lower() for role in required_roles]

        # Method 1: Check custom role field
        if hasattr(user, "role") and user.role:
            return user.role.lower() in required_roles_lower

        # Method 2: Check Django groups
        if hasattr(user, "groups"):
            user_groups = [group.name.lower() for group in user.groups.all()]
            if any(group in required_roles_lower for group in user_groups):
                return True

        # Method 3: Check Django staff/superuser status
        if "admin" in required_roles_lower and (user.is_staff or user.is_superuser):
            return True

        if "moderator" in required_roles_lower and user.is_staff:
            return True

        return False
