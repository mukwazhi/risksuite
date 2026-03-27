"""
Management command to fix invalid decimal fields in RiskIndicator model
"""
from django.core.management.base import BaseCommand
from riskregister.models import RiskIndicator
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = 'Fix invalid decimal values in RiskIndicator fields'

    def handle(self, *args, **options):
        self.stdout.write('Checking and fixing invalid decimal fields...')
        
        fixed_count = 0
        error_count = 0
        
        # Get all indicators
        indicators = RiskIndicator.objects.all()
        
        for indicator in indicators:
            try:
                # Try to access decimal fields to see if they're valid
                fields_to_check = [
                    ('appetite_tolerance_pct', Decimal('10.00')),
                    ('trigger_threshold', None),
                    ('breach_threshold', None),
                ]
                
                for field_name, default_value in fields_to_check:
                    try:
                        value = getattr(indicator, field_name)
                        if value is not None:
                            # Try to convert to decimal to verify it's valid
                            Decimal(str(value))
                    except (InvalidOperation, ValueError, TypeError) as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Invalid {field_name} for indicator {indicator.pk}: {e}'
                            )
                        )
                        # Set to default value
                        setattr(indicator, field_name, default_value)
                        indicator.save()
                        fixed_count += 1
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing indicator {indicator.pk}: {e}')
                )
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Done! Fixed {fixed_count} fields. Errors: {error_count}'
            )
        )
