"""
Management command to process assessment schedules and trigger risk assessments
Run this daily via cron or task scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from riskregister.models import (
    PeriodicMeasurementSchedule, 
    AssessmentScheduleConfig,
    Risk,
    IndicatorAssessment
)
from riskregister.services.assessment_aggregation import AssessmentAggregationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process due assessment schedules and check for auto-triggered risk assessments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='Send reminders for assessments due in this many days'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        today = date.today()
        reminder_date = today + timedelta(days=days_ahead)
        
        # Process overdue assessments
        self.stdout.write('\n=== Processing Overdue Assessments ===')
        self._process_overdue_assessments(today, dry_run)
        
        # Send reminders for upcoming assessments
        self.stdout.write('\n=== Sending Assessment Reminders ===')
        self._send_assessment_reminders(reminder_date, dry_run)
        
        # Check for auto-triggered risk assessments
        self.stdout.write('\n=== Checking Auto-Trigger Conditions ===')
        self._check_auto_triggers(dry_run)
        
        # Generate schedules for risks that need them
        self.stdout.write('\n=== Generating Missing Schedules ===')
        self._generate_missing_schedules(dry_run)
        
        self.stdout.write(self.style.SUCCESS('\n✓ Assessment processing complete'))
    
    def _process_overdue_assessments(self, today, dry_run):
        """Mark overdue assessments and send notifications"""
        
        overdue_schedules = PeriodicMeasurementSchedule.objects.filter(
            scheduled_date__lt=today,
            status='pending'
        ).select_related('indicator', 'indicator__risk')
        
        count = overdue_schedules.count()
        self.stdout.write(f'Found {count} overdue assessment(s)')
        
        for schedule in overdue_schedules:
            days_overdue = (today - schedule.scheduled_date).days
            self.stdout.write(
                f'  • {schedule.indicator.preferred_kpi_name} '
                f'(Risk: {schedule.indicator.risk.risk_id}) - {days_overdue} days overdue'
            )
            
            if not dry_run:
                # Mark as overdue (you can add a status field for this)
                # For now, we'll just log it
                logger.warning(
                    f'Overdue assessment: {schedule.indicator.preferred_kpi_name} '
                    f'for risk {schedule.indicator.risk.risk_id}'
                )
    
    def _send_assessment_reminders(self, reminder_date, dry_run):
        """Send reminders for upcoming assessments"""
        
        upcoming_schedules = PeriodicMeasurementSchedule.objects.filter(
            scheduled_date=reminder_date,
            status='pending',
            reminder_sent=False
        ).select_related('indicator', 'indicator__risk')
        
        count = upcoming_schedules.count()
        self.stdout.write(f'Found {count} assessment(s) needing reminders')
        
        for schedule in upcoming_schedules:
            self.stdout.write(
                f'  • {schedule.indicator.preferred_kpi_name} '
                f'(Risk: {schedule.indicator.risk.risk_id}) - due {schedule.scheduled_date}'
            )
            
            if not dry_run:
                # Send notification (integrate with your notification system)
                self._send_reminder_notification(schedule)
                
                # Mark reminder as sent
                schedule.reminder_sent = True
                schedule.reminder_sent_at = timezone.now()
                schedule.save(update_fields=['reminder_sent', 'reminder_sent_at'])
    
    def _send_reminder_notification(self, schedule):
        """Send notification for upcoming assessment"""
        # Notification system has been removed; log reminder action instead.
        logger.info(
            f'(notifications removed) Reminder for {schedule.indicator.preferred_kpi_name} '
            f'(Risk: {schedule.indicator.risk.risk_id})'
        )
    
    def _check_auto_triggers(self, dry_run):
        """Check if any risks should have auto-triggered assessments"""
        
        configs = AssessmentScheduleConfig.objects.filter(
            is_active=True
        ).select_related('risk')
        
        triggered_count = 0
        
        for config in configs:
            risk = config.risk
            
            # Get recent assessments (last 30 days)
            period_start = date.today() - timedelta(days=30)
            recent_assessments = IndicatorAssessment.objects.filter(
                indicator__risk=risk,
                assessment_date__gte=period_start,
                triggered_risk_assessment=False
            )
            
            breached_count = recent_assessments.filter(status='breached').count()
            
            if breached_count >= config.auto_trigger_on_breached:
                self.stdout.write(
                    f'  • Risk {risk.risk_id}: {breached_count} breached indicators '
                    f'(threshold: {config.auto_trigger_on_breached}) - TRIGGERING'
                )
                
                if not dry_run:
                    assessment = AssessmentAggregationService.check_auto_trigger_conditions(risk)
                    if assessment:
                        triggered_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    ✓ Created risk assessment {assessment.id}'
                            )
                        )
        
        if triggered_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Triggered {triggered_count} risk assessment(s)'))
        else:
            self.stdout.write('No risks meet auto-trigger conditions')
    
    def _generate_missing_schedules(self, dry_run):
        """Generate schedules for risks that don't have recent schedules"""
        
        configs = AssessmentScheduleConfig.objects.filter(is_active=True)
        
        generated_count = 0
        
        for config in configs:
            # Check if schedules need to be generated
            if config.last_generated is None or \
               (date.today() - config.last_generated).days > 30:
                
                self.stdout.write(
                    f'  • Generating schedules for risk {config.risk.risk_id}'
                )
                
                if not dry_run:
                    try:
                        config.generate_schedules()
                        generated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    ✓ Generated schedules for {config.risk.risk_id}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'    ✗ Error generating schedules: {e}'
                            )
                        )
        
        if generated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Generated schedules for {generated_count} risk(s)'))
        else:
            self.stdout.write('All schedules are up to date')
