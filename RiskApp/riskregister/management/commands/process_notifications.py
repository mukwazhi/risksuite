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
from riskregister.models import GlobalNotificationConfig
from riskregister.utils.notifications import send_notifications_for_user
import logging
from riskregister.utils.notifications import notify_staff_of_outstanding_items
from django.core.cache import cache
from django.core.mail import get_connection
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process and send notification emails for users based on their preferences.'

    def add_arguments(self, parser):
        parser.add_argument('--test-user', help='Email or username of user to send a test notification to')
        parser.add_argument('--debug-all', action='store_true', help='Print detailed queries/results for all users to console')
        parser.add_argument('--staff-summary', action='store_true', help='Send aggregated outstanding items summary to staff/superusers')

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

        if options.get('staff_summary'):
            # Send aggregated outstanding items summary to staff
            self.stdout.write('Sending aggregated outstanding items summary to staff...')
            try:
                count = notify_staff_of_outstanding_items()
                self.stdout.write(self.style.SUCCESS(f'Sent aggregated summary to {count} staff recipient(s)'))
            except Exception as e:
                logger.exception('Error sending staff aggregated summary: %s', e)
                self.stdout.write(self.style.ERROR('Failed to send staff aggregated summary'))
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
            now = timezone.localtime()

            # Load global config (if any)
            try:
                global_cfg = GlobalNotificationConfig.objects.order_by('-updated_at').first()
            except Exception:
                global_cfg = None

            def should_send(pref):
                # Immediate frequency: always send when scheduler runs
                # Use global frequency/time when enabled
                effective_notify_time = None
                effective_frequency = pref.frequency
                if global_cfg and global_cfg.enabled:
                    if global_cfg.notify_time:
                        effective_notify_time = global_cfg.notify_time
                    effective_frequency = global_cfg.frequency or pref.frequency

                if effective_frequency == 'immediate':
                    return True
                # Respect notify_time if set: if set, only send when current time
                # is within a small window (5 minutes) of the preferred time.
                use_time = effective_notify_time or pref.notify_time
                if use_time:
                    notify_dt = now.replace(hour=use_time.hour, minute=use_time.minute, second=0, microsecond=0)
                    window_start = notify_dt - timedelta(minutes=5)
                    window_end = notify_dt + timedelta(minutes=5)
                    if not (window_start <= now <= window_end):
                        return False

                # Frequency enforcement using cached last-sent timestamp to avoid DB migration.
                cache_key = f'notification_last_sent_{pref.user.pk}'
                last_sent = cache.get(cache_key)
                if last_sent:
                    try:
                        last_sent_dt = timezone.make_aware(datetime.fromtimestamp(float(last_sent)))
                    except Exception:
                        last_sent_dt = None
                else:
                    last_sent_dt = None

                # Use effective_frequency (global override possible)
                if effective_frequency == 'daily':
                    if last_sent_dt and last_sent_dt.date() == now.date():
                        return False
                    return True
                if effective_frequency == 'weekly':
                    if last_sent_dt and (now - last_sent_dt) < timedelta(days=7):
                        return False
                    return True
                if effective_frequency == 'monthly':
                    if last_sent_dt and (now - last_sent_dt) < timedelta(days=28):
                        return False
                    return True
                if effective_frequency == 'quarterly':
                    if last_sent_dt and (now - last_sent_dt) < timedelta(days=85):
                        return False
                    return True

                # Fallback: send
                return True

            for pref in prefs:
                try:
                    if not should_send(pref):
                        continue
                    res = send_notifications_for_user(pref.user, test=False)
                    if res:
                        # mark last sent time in cache
                        cache.set(f'notification_last_sent_{pref.user.pk}', str(timezone.now().timestamp()), 60 * 60 * 24 * 365)
                        sent += res
                except Exception as e:
                    logger.exception('Error sending notifications for %s: %s', pref.user, e)

        self.stdout.write(self.style.SUCCESS(f'Sent {sent} notification email(s)'))
