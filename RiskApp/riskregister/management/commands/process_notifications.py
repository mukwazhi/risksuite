"""
Process notification emails according to each user's `NotificationPreference`.

This command is intended to be run periodically (cron/scheduler) or invoked
from a Celery beat task. For development, use the console email backend in
settings so outgoing emails appear in the server terminal.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from riskregister.models import NotificationPreference
from riskregister.utils.notifications import send_notifications_for_user
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process and send notification emails for users based on their preferences.'

    def add_arguments(self, parser):
        parser.add_argument('--test-user', help='Email or username of user to send a test notification to')
        parser.add_argument('--debug-all', action='store_true', help='Print detailed queries/results for all users to console')

    def handle(self, *args, **options):
        User = get_user_model()

        test_user = options.get('test_user')
        sent = 0

        if test_user:
            # Try email first, then username
            user = User.objects.filter(email__iexact=test_user).first() or User.objects.filter(username__iexact=test_user).first()
            if not user:
                self.stdout.write(self.style.ERROR(f'No user found for "{test_user}"'))
                return
            self.stdout.write(self.style.WARNING(f'Sending test notification to {user}'))
            # Use console backend for test sends so output appears in this terminal
            from django.core.mail import get_connection
            conn = get_connection(backend='django.core.mail.backends.console.EmailBackend')
            sent += send_notifications_for_user(user, test=True, connection=conn)
            self.stdout.write(self.style.SUCCESS(f'Sent {sent} test notification(s)'))
            return

        # Normal run: iterate all users who have preferences and want email
        prefs = NotificationPreference.objects.filter(enable_email_notifications=True).select_related('user')
        self.stdout.write(f'Found {prefs.count()} users with email notifications enabled')

        if options.get('debug_all'):
            # Use console backend and print detailed queries for all users
            conn = get_connection(backend='django.core.mail.backends.console.EmailBackend')
            for pref in prefs:
                try:
                    sent += send_notifications_for_user(pref.user, test=False, connection=conn, actor=None, show_queries=True)
                except Exception as e:
                    logger.exception('Error sending notifications for %s: %s', pref.user, e)
        else:
            for pref in prefs:
                try:
                    sent += send_notifications_for_user(pref.user, test=False)
                except Exception as e:
                    logger.exception('Error sending notifications for %s: %s', pref.user, e)

        self.stdout.write(self.style.SUCCESS(f'Sent {sent} notification email(s)'))
