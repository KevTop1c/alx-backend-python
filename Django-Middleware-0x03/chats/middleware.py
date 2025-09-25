"""Module imports for middleware"""

import datetime
import os
import logging
from django.conf import settings
from django.http import HttpResponseForbidden


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
                with open(self.log_file, "a"):
                    pass
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")

    def __call__(self, request, *args, **kwds):
        try:
            user = "Anonymous"
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

        except Exception as e:
            logger.error(f"Requesting logging file failed: {e}")

        # Process the request
        response = self.get_response(request)

        return response


class RestrictAccessByTimeMiddleware:
    """Custom access restriction middleware"""

    def __init__(self, get_response):
        self.get_response = get_response
        # Configurable restricted hours: 9PM (21:00) and 6PM (18:00)
        self.start_restriction = datetime.time(21, 0)
        self.end_restriction = datetime.time(18, 0)

    def __call__(self, request, *args, **kwds):
        # Get current server time
        current_time = datetime.datetime.now().time()

        # Check if current time is within restricted hours (9PM and 6PM)
        if self.is_restricted_time(current_time):
            return HttpResponseForbidden(
                f"Access denied: The messaging service is available between "
                f"6:00 PM and 9:00 PM. Current time: {current_time.strftime("%I:%M %p")}"
            )

        # If outside restricted time, process normally
        response = self.get_response(request)
        return response

    def is_restricted_time(self, current_time):
        """
        Check if current time is within restricted hours (9 PM to 6 PM)
        Since 9 PM > 6 PM, this covers:
        - From 9 PM to midnight (21:00-23:59)
        - From midnight to 6 PM (00:00-18:00)
        """
        return (current_time >= self.start_restriction) or (
            current_time <= self.end_restriction
        )
