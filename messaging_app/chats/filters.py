from datetime import timedelta
from django.utils import timezone
from django_filters import rest_framework as filters
from .models import Message


PERIOD_CHOICES = (
    ("today", "Today"),
    ("last_7_days", "Last 7 Days"),
)


class MessageFilter(filters.FilterSet):
    """Advanced filter for messages"""

    conversation = filters.UUIDFilter(field_name="conversation_id")
    sender = filters.UUIDFilter(field_name="sender_id")

    # Date range
    sent_range = filters.DateFromToRangeFilter(
        field_name="sent_at",
        help_text="Filter messages between two dates (?sent_range_after= & ?sent_range_before=)",
    )

    # Period (business logic shortcut)
    period = filters.ChoiceFilter(
        choices=PERIOD_CHOICES,
        method="filter_period",
        help_text="Filter by predefined periods: today, last_7_days",
    )

    # Search
    search = filters.CharFilter(
        field_name="message_body",
        lookup_expr="icontains",
        help_text="Search for text in message body",
    )

    class Meta:
        """MessageFilter definition"""
        model = Message
        fields = ["conversation", "sender", "sent_range"]

    def filter_period(self, queryset, _name, value):
        """Filter period for message"""
        now = timezone.now()
        if value == "today":
            return queryset.filter(sent_at__date=now.date())
        elif value == "last_7_days":
            return queryset.filter(sent_at__gte=now - timedelta(days=7))
        return queryset
