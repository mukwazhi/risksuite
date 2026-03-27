"""
Django management command to update existing risks to approved status
"""
from django.core.management.base import BaseCommand
from riskregister.models import Risk


class Command(BaseCommand):
    help = 'Update existing risks to approved status'

    def handle(self, *args, **options):
        # Update all existing risks that don't have a status or have 'parked' status
        updated = Risk.all_objects.filter(status='parked').update(
            status='approved',
            is_approved=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated} risks to approved status')
        )
