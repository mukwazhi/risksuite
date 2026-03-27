"""
Deactivate users whose `NotificationPreference.expiry_date` has passed.

Intended to be run periodically (cron / scheduled job). Supports `--dry-run`
to show which accounts would be deactivated without making changes.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from riskregister.models import NotificationPreference
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deactivate users whose NotificationPreference.expiry_date has passed.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show users that would be deactivated without changing them')

    def handle(self, *args, **options):
        now = timezone.now()
        prefs = NotificationPreference.objects.filter(expiry_date__isnull=False, expiry_date__lte=now).select_related('user')
        total = prefs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No expired users found'))
            return

        dry_run = options.get('dry_run')
        self.stdout.write(f'Found {total} users with expiry_date <= {now.isoformat()}')

        deactivated = 0
        for pref in prefs:
            user = pref.user
            if not user:
                continue
            if not user.is_active:
                self.stdout.write(f'Skipping already inactive user: {user} ({user.email})')
                continue

            if dry_run:
                self.stdout.write(f'[DRY RUN] Would deactivate user: {user} ({user.email})')
                continue

            try:
                user.is_active = False
                user.save(update_fields=['is_active'])
                deactivated += 1
                self.stdout.write(self.style.SUCCESS(f'Deactivated user: {user} ({user.email})'))
            except Exception as e:
                logger.exception('Error deactivating user %s: %s', user, e)
                self.stdout.write(self.style.ERROR(f'Error deactivating user: {user} ({e})'))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'Deactivated {deactivated} user(s)'))
