"""
Dump RiskOwner records and related risks to the console.

Usage:
  python manage.py dump_risk_owners
  python manage.py dump_risk_owners --create-missing

The `--create-missing` option will create `RiskOwner` entries for active users
that do not already have a `RiskOwner` profile, only when a single default
`Department` is available. This avoids assigning arbitrary departments.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from riskregister.models import RiskOwner, Risk, Department


class Command(BaseCommand):
    help = 'Dump all RiskOwner records and their linked risks to the console.'

    def add_arguments(self, parser):
        parser.add_argument('--create-missing', action='store_true', help='Create RiskOwner records for users without one (only if a single Department exists)')

    def handle(self, *args, **options):
        User = get_user_model()
        create_missing = options.get('create_missing', False)

        # List existing RiskOwners
        owners = RiskOwner.objects.select_related('department', 'user').all()
        if not owners.exists():
            self.stdout.write(self.style.WARNING('No RiskOwner records found.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Found {owners.count()} RiskOwner record(s):'))
            for o in owners:
                user_display = o.user.username if o.user else '<no linked user>'
                dept = o.department.name if o.department else '<no department>'
                risks = Risk.objects.filter(risk_owner=o).order_by('risk_number')
                self.stdout.write('-' * 60)
                self.stdout.write(f'Name: {o.name}')
                self.stdout.write(f'Linked user: {user_display}')
                self.stdout.write(f'Email: {o.email or "<no email>"} | Phone: {o.phone_number or "<no phone>"}')
                self.stdout.write(f'Department: {dept}')
                self.stdout.write(f'Linked risks: {risks.count()}')
                if risks.exists():
                    for r in risks:
                        try:
                            self.stdout.write(f'  - {r.risk_id}: {r.title} (status={r.status})')
                        except Exception:
                            self.stdout.write(f'  - Risk id={r.pk} (title unavailable)')

        # Optionally create missing RiskOwner records for active users
        if create_missing:
            self.stdout.write('\nChecking for users without RiskOwner profiles...')
            users_without = User.objects.filter(is_active=True).exclude(risk_owner_profile__isnull=False)
            if not users_without.exists():
                self.stdout.write(self.style.SUCCESS('All active users already have RiskOwner profiles.'))
                return

            depts = Department.objects.all()
            if depts.count() != 1:
                self.stdout.write(self.style.ERROR('Cannot auto-create RiskOwner: requires exactly one Department to assign.'))
                self.stdout.write('Found departments:')
                for d in depts:
                    self.stdout.write(f' - {d.name} ({d.abbreviation})')
                self.stdout.write('Either create a default Department or create RiskOwner records manually.')
                return

            default_dept = depts.first()
            created = 0
            for user in users_without:
                name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username
                ro = RiskOwner.objects.create(
                    name=name,
                    email=user.email or None,
                    phone_number=None,
                    department=default_dept,
                    user=user,
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created RiskOwner for user {user.username} -> {ro}'))

            self.stdout.write(self.style.SUCCESS(f'Created {created} RiskOwner record(s).'))

        # Final summary timestamp
        self.stdout.write('\nDump completed at {0}'.format(timezone.now()))
