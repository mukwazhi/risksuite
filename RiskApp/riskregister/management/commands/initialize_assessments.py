"""
Management command to initialize assessment schedules for existing risks.
Run this once after implementing the assessment framework.

Usage:
    python manage.py initialize_assessments [--frequency FREQ] [--auto-trigger N]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from riskregister.models import Risk, AssessmentScheduleConfig
from django.utils import timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'Initialize assessment schedule configurations for existing risks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=str,
            default='quarterly',
            choices=['monthly', 'quarterly', 'semi_annual', 'annual'],
            help='Default assessment frequency (default: quarterly)'
        )
        parser.add_argument(
            '--auto-trigger',
            type=int,
            default=2,
            help='Default number of breached indicators to auto-trigger assessment (default: 2)'
        )
        parser.add_argument(
            '--skip-schedules',
            action='store_true',
            help='Only create configs without generating schedules'
        )

    def handle(self, *args, **options):
        frequency = options['frequency']
        auto_trigger = options['auto_trigger']
        skip_schedules = options['skip_schedules']

        self.stdout.write(self.style.WARNING(
            f"\n{'='*70}\n"
            f"  Assessment Framework Initialization\n"
            f"{'='*70}\n"
        ))

        # Get all approved/active risks
        risks = Risk.objects.filter(status__in=['approved', 'active'])
        total_risks = risks.count()
        
        if total_risks == 0:
            self.stdout.write(self.style.WARNING("No approved or active risks found."))
            return

        self.stdout.write(f"\nFound {total_risks} approved/active risks")
        self.stdout.write(f"Default frequency: {frequency}")
        self.stdout.write(f"Auto-trigger threshold: {auto_trigger} breached indicators\n")

        created_count = 0
        existing_count = 0
        schedules_generated = 0
        errors = []

        with transaction.atomic():
            for risk in risks:
                try:
                    config, created = AssessmentScheduleConfig.objects.get_or_create(
                        risk=risk,
                        defaults={
                            'is_active': True,
                            'risk_assessment_frequency': frequency,
                            'auto_trigger_on_breached': auto_trigger,
                            'schedule_advance_months': 12,
                            'min_indicator_assessments': 1,
                        }
                    )

                    if created:
                        created_count += 1
                        status_icon = self.style.SUCCESS("✓")
                        
                        # Generate schedules if not skipped
                        if not skip_schedules:
                            try:
                                # Use the main generate_schedules method
                                config.generate_schedules()
                                
                                # Count generated schedules
                                from riskregister.models import PeriodicMeasurementSchedule
                                indicator_count = PeriodicMeasurementSchedule.objects.filter(
                                    indicator__risk=risk
                                ).count()
                                
                                self.stdout.write(
                                    f"{status_icon} Created config for Risk #{risk.risk_number} "
                                    f"({indicator_count} schedules generated)"
                                )
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  ⚠ Schedule generation failed: {str(e)}"
                                    )
                                )
                        else:
                            self.stdout.write(
                                f"{status_icon} Created config for Risk #{risk.risk_number}"
                            )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            f"  - Risk #{risk.risk_number} already has config"
                        )

                except Exception as e:
                    error_msg = f"Risk #{risk.risk_number}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed: {error_msg}")
                    )

        # Summary
        self.stdout.write(self.style.WARNING(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count} new configurations"))
        self.stdout.write(f"Existing: {existing_count} configurations")
        
        if not skip_schedules:
            self.stdout.write(self.style.SUCCESS(f"Generated: {schedules_generated} assessment schedules"))
        
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write(self.style.WARNING(f"{'='*70}\n"))

        # Next steps
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS("\n✓ Initialization complete!\n"))
            self.stdout.write("Next steps:")
            self.stdout.write("  1. Review configs in admin or create a management view")
            self.stdout.write("  2. Set up cron job for daily processing:")
            self.stdout.write("     0 9 * * * python manage.py process_assessment_schedules")
            self.stdout.write("  3. Test with: python manage.py process_assessment_schedules --dry-run\n")
        else:
            self.stdout.write(self.style.WARNING("\nAll risks already have assessment configurations.\n"))
