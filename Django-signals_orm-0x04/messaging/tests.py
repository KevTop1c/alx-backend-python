from django.test import TestCase
from django.contrib.auth.models import User
from .models import Message, Notification


# pylint: disable=no-member
class MessageModelTest(TestCase):
    """Test cases for Message model"""

    def setUp(self):
        """Set up test users"""
        self.user1 = User.objects.create_user(
            username="sender", email="sender@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="receiver", email="receiver@test.com", password="testpass123"
        )

    def test_message_creation(self):
        """Test that a message can be created"""
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Hello, this is a test message!",
        )
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.receiver, self.user2)
        self.assertEqual(message.content, "Hello, this is a test message!")
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.timestamp)

    def test_message_string_representation(self):
        """Test the string representation of a message"""
        message = Message.objects.create(
            sender=self.user1, receiver=self.user2, content="Test"
        )
        self.assertIn(self.user1.username, str(message))
        self.assertIn(self.user2.username, str(message))


class NotificationSignalTest(TestCase):
    """Test cases for notification signals"""

    def setUp(self):
        """Set up test users"""
        self.user1 = User.objects.create_user(
            username="sender", email="sender@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="receiver", email="receiver@test.com", password="testpass123"
        )

    def test_notification_created_on_new_message(self):
        """Test that a notification is automatically created when a message is sent"""
        # Initial notification count
        initial_count = Notification.objects.count()

        # Create a new message
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Test message for notification",
        )

        # Check that a notification was created
        self.assertEqual(Notification.objects.count(), initial_count + 1)

        # Verify the notification details
        notification = Notification.objects.latest("timestamp")
        self.assertEqual(notification.user, self.user2)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.notification_type, "message")
        self.assertIn(self.user1.username, notification.content)
        self.assertFalse(notification.is_read)

    def test_no_notification_on_message_update(self):
        """Test that updating a message doesn't create a new notification"""
        # Create a message (this will create one notification)
        message = Message.objects.create(
            sender=self.user1, receiver=self.user2, content="Original content"
        )

        initial_count = Notification.objects.count()

        # Update the message
        message.is_read = True
        message.save()

        # Notification count should remain the same
        self.assertEqual(Notification.objects.count(), initial_count)

    def test_multiple_messages_create_multiple_notifications(self):
        """Test that multiple messages create multiple notifications"""
        initial_count = Notification.objects.count()

        # Send 3 messages
        for i in range(3):
            Message.objects.create(
                sender=self.user1, receiver=self.user2, content=f"Message number {i+1}"
            )

        # Check that 3 notifications were created
        self.assertEqual(Notification.objects.count(), initial_count + 3)

        # Verify all notifications are for the receiver
        notifications = Notification.objects.filter(user=self.user2)
        self.assertEqual(notifications.count(), initial_count + 3)


class NotificationModelTest(TestCase):
    """Test cases for Notification model"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="testpass123"
        )
        self.message = Message.objects.create(
            sender=self.user1, receiver=self.user2, content="Test message"
        )

    def test_notification_mark_as_read(self):
        """Test marking a notification as read"""
        notification = Notification.objects.get(user=self.user2, message=self.message)
        self.assertFalse(notification.is_read)

        notification.mark_as_read()

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_notification_string_representation(self):
        """Test the string representation of a notification"""
        notification = Notification.objects.get(user=self.user2, message=self.message)
        self.assertIn(self.user2.username, str(notification))

    def test_notification_truncated_content(self):
        """Test that long message content is truncated in notifications"""
        long_content = "A" * 100  # 100 character message
        long_message = Message.objects.create(
            sender=self.user1, receiver=self.user2, content=long_content
        )

        notification = Notification.objects.get(message=long_message)
        # Notification should have truncated content with ellipsis
        self.assertLess(len(notification.content), len(long_content) + 50)
        self.assertIn("...", notification.content)


class MessageQueryTest(TestCase):
    """Test cases for querying messages and notifications"""

    def setUp(self):
        """Set up test users and messages"""
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")
        self.user3 = User.objects.create_user(username="user3", password="pass")

        # Create several messages
        Message.objects.create(sender=self.user1, receiver=self.user2, content="Msg 1")
        Message.objects.create(sender=self.user2, receiver=self.user1, content="Msg 2")
        Message.objects.create(sender=self.user3, receiver=self.user1, content="Msg 3")

    def test_user_received_messages(self):
        """Test querying messages received by a user"""
        received = self.user1.received_messages.all()
        self.assertEqual(received.count(), 2)

    def test_user_sent_messages(self):
        """Test querying messages sent by a user"""
        sent = self.user1.sent_messages.all()
        self.assertEqual(sent.count(), 1)

    def test_user_notifications(self):
        """Test querying notifications for a user"""
        notifications = self.user1.notifications.all()
        self.assertEqual(notifications.count(), 2)  # Received 2 messages
