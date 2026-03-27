from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from riskregister.models import Mitigation, RiskOwner
from datetime import datetime
import csv


class Command(BaseCommand):
    help = 'Fill missing Mitigation responsible_person and/or due_date values from a CSV mapping or defaults.'

    def add_arguments(self, parser):
        parser.add_argument('--mapping-file', type=str, help='CSV file with columns: mitigation_id,responsible_person_id,due_date (YYYY-MM-DD)')
        parser.add_argument('--default-responsible', type=int, help='RiskOwner id to assign when responsible_person is missing')
        parser.add_argument('--default-due', type=str, help='Default due date (YYYY-MM-DD) to apply when due_date is missing')
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **options):
        mapping_file = options.get('mapping_file')
        default_responsible = options.get('default_responsible')
        default_due = options.get('default_due')
        dry_run = options.get('dry_run')

        if not mapping_file and not default_responsible and not default_due:
            raise CommandError('Provide at least --mapping-file or one of --default-responsible/--default-due')

        # Validate default responsible exists
        default_owner = None
        if default_responsible:
            try:
                default_owner = RiskOwner.objects.get(pk=default_responsible)
            except RiskOwner.DoesNotExist:
                raise CommandError(f'RiskOwner with id {default_responsible} does not exist')

        default_due_date = None
        if default_due:
            try:
                default_due_date = datetime.strptime(default_due, '%Y-%m-%d').date()
            except Exception:
                raise CommandError('Invalid --default-due format, expected YYYY-MM-DD')

        updated = 0
        skipped = 0

        # Apply mappings from CSV first (if provided)
        if mapping_file:
            try:
                with open(mapping_file, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        mid = row.get('mitigation_id') or row.get('id')
                        if not mid:
                            self.stdout.write(self.style.WARNING('Skipping row without mitigation_id'))
                            continue
                        try:
                            m = Mitigation.objects.get(pk=int(mid))
                        except Mitigation.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'Mitigation {mid} not found, skipping'))
                            skipped += 1
                            continue

                        rp = row.get('responsible_person_id')
                        due = row.get('due_date')

                        changed = False
                        if rp and (not m.responsible_person):
                            try:
                                owner = RiskOwner.objects.get(pk=int(rp))
                                if not dry_run:
                                    m.responsible_person = owner
                                    m.save(update_fields=['responsible_person'])
                                changed = True
                            except RiskOwner.DoesNotExist:
                                self.stdout.write(self.style.WARNING(f'RiskOwner {rp} not found for mitigation {mid}'))

                        if due and (not m.due_date):
                            try:
                                parsed = datetime.strptime(due.strip(), '%Y-%m-%d').date()
                                if not dry_run:
                                    m.due_date = parsed
                                    m.save(update_fields=['due_date'])
                                changed = True
                            except Exception:
                                self.stdout.write(self.style.WARNING(f'Invalid date {due} for mitigation {mid}'))

                        if changed:
                            updated += 1
            except FileNotFoundError:
                raise CommandError(f'Mapping file not found: {mapping_file}')

        # Apply defaults to all mitigations with missing fields
        qs = Mitigation.objects.all()
        for m in qs:
            to_update = {}
            if (not m.responsible_person) and default_owner:
                to_update['responsible_person'] = default_owner
            if (not m.due_date) and default_due_date:
                to_update['due_date'] = default_due_date

            if to_update:
                self.stdout.write(f"Mitigation {m.pk}: will set {', '.join(to_update.keys())}")
                if not dry_run:
                    for k, v in to_update.items():
                        setattr(m, k, v)
                    m.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Updated {updated} mitigations. Skipped {skipped} rows.'))