"""
Notification helpers: build and send notification emails for users.

This implementation uses Django's email backend so the project setting
`EMAIL_BACKEND` controls behavior. For local development set
`EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`
to print emails to the server terminal.
"""
from datetime import date, datetime, timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from typing import Optional

from ..models import NotificationPreference
from ..models import PeriodicMeasurementSchedule, Mitigation
from ..models import RiskOwner
from django.contrib.auth import get_user_model
from django.core.mail.backends.console import EmailBackend as DjangoConsoleEmailBackend
import textwrap
from typing import Dict, List
from django.db import models

logger = logging.getLogger(__name__)


def _gather_assessment_items_for_user(user, pref: NotificationPreference):
    today = date.today()
    items = {
        'pending': [],
        'upcoming': [],
        'overdue': [],
    }
    queries: dict[str, Optional[str]] = {
        'pending': None,
        'upcoming': None,
        'overdue': None,
    }

    # Pending assessments: status pending
    if pref.enable_pending_assessments:
        qs = PeriodicMeasurementSchedule.objects.filter(status='pending').select_related('indicator', 'indicator__risk')
        qs = qs.filter(indicator__risk__risk_owner__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['pending'] = str(qs.query)
        except Exception:
            queries['pending'] = None
        for s in qs:
            items['pending'].append(s)

    # Upcoming assessments
    if pref.enable_upcoming_assessments:
        end_date = today + timedelta(days=pref.upcoming_days_assessment)
        qs = PeriodicMeasurementSchedule.objects.filter(status='pending', scheduled_date__gte=today, scheduled_date__lte=end_date).select_related('indicator', 'indicator__risk')
        qs = qs.filter(indicator__risk__risk_owner__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['upcoming'] = str(qs.query)
        except Exception:
            queries['upcoming'] = None
        for s in qs:
            items['upcoming'].append(s)

    # Overdue assessments
    if pref.enable_overdue_assessments:
        qs = PeriodicMeasurementSchedule.objects.filter(status='pending', scheduled_date__lt=today).select_related('indicator', 'indicator__risk')
        qs = qs.filter(indicator__risk__risk_owner__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['overdue'] = str(qs.query)
        except Exception:
            queries['overdue'] = None
        for s in qs:
            items['overdue'].append(s)

    return items, queries


def _gather_mitigation_items_for_user(user, pref: NotificationPreference):
    today = date.today()
    items = {
        'pending': [],
        'upcoming': [],
        'overdue': [],
    }
    queries = {
        'pending': None,
        'upcoming': None,
        'overdue': None,
    }

    # Pending mitigations - not completed
    if pref.enable_pending_mitigations:
        qs = Mitigation.objects.filter(status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person')
        qs = qs.filter(responsible_person__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['pending'] = str(qs.query)
        except Exception:
            queries['pending'] = None
        for m in qs:
            items['pending'].append(m)

    # Upcoming mitigations
    if pref.enable_upcoming_mitigations:
        end_date = today + timedelta(days=pref.upcoming_days_mitigation)
        qs = Mitigation.objects.filter(due_date__gte=today, due_date__lte=end_date, status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person')
        qs = qs.filter(responsible_person__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['upcoming'] = str(qs.query)
        except Exception:
            queries['upcoming'] = None
        for m in qs:
            items['upcoming'].append(m)

    # Overdue mitigations
    if pref.enable_overdue_mitigations:
        qs = Mitigation.objects.filter(due_date__lt=today, status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person')
        qs = qs.filter(responsible_person__user=user) if hasattr(user, 'id') else qs.none()
        try:
            queries['overdue'] = str(qs.query)
        except Exception:
            queries['overdue'] = None
        for m in qs:
            items['overdue'].append(m)

    return items, queries


def send_notifications_for_user(user, test=False, connection=None, actor=None, show_queries=False):
    """Build and send an individualized notification email for `user`.

    If `test` is True, send a sample message regardless of actual items.
    Returns 1 when an email was sent, 0 otherwise.
    """
    # Allow test sends even if the user has no stored preferences.
    if test:
        # Create an in-memory preference object with sensible defaults
        pref = NotificationPreference(
            user=user,
            enable_email_notifications=True,
            enable_pending_assessments=True,
            enable_upcoming_assessments=True,
            enable_overdue_assessments=True,
            upcoming_days_assessment=2,
            enable_pending_mitigations=True,
            enable_upcoming_mitigations=True,
            enable_overdue_mitigations=True,
            upcoming_days_mitigation=2,
            frequency='daily'
        )
    else:
        try:
            pref = user.notification_preference
        except NotificationPreference.DoesNotExist:
            logger.debug('No NotificationPreference for user %s', user)
            return 0

        if not pref.enable_email_notifications:
            logger.debug('Email notifications disabled for user %s', user)
            return 0

    if not test:
        assessment_items, assessment_queries = _gather_assessment_items_for_user(user, pref)
        mitigation_items, mitigation_queries = _gather_mitigation_items_for_user(user, pref)
    else:
        assessment_items, assessment_queries = ({'pending': [], 'upcoming': [], 'overdue': []}, {})
        mitigation_items, mitigation_queries = ({'pending': [], 'upcoming': [], 'overdue': []}, {})

    # If test mode and no real items, include a sample entry
    if test:
        sample_text = 'This is a test notification demonstrating your current preferences.'
    else:
        sample_text = None

    # Build email context
    context = {
        'user': user,
        'assessment_items': assessment_items,
        'mitigation_items': mitigation_items,
        'sample_text': sample_text,
        'generated_at': datetime.now(),
        'preferences': pref,
    }

    subject = f'RiskSuite notifications for {user.get_full_name() or user.username}'
    html_body = render_to_string('riskregister/email/notification_email.html', context)

    # Build a clear plain-text body that mirrors the DB queries performed
    def _format_items_section(title, items_map, item_type):
        lines = []
        total = sum(len(v) for v in items_map.values() if v)
        lines.append(f"{title} ({total})")
        for key in ('pending', 'upcoming', 'overdue'):
            lst = items_map.get(key, [])
            if not lst:
                continue
            lines.append(f"\n{key.capitalize()} ({len(lst)}):")
            for obj in lst:
                if item_type == 'assessment':
                    try:
                        name = obj.indicator.preferred_kpi_name
                        due = getattr(obj, 'scheduled_date', 'N/A')
                        risk_id = obj.indicator.risk.risk_id if getattr(obj.indicator, 'risk', None) else getattr(obj.indicator, 'risk_id', 'N/A')
                        lines.append(f" - {name} — due {due} (Risk: {risk_id})")
                    except Exception:
                        lines.append(f" - Assessment id={getattr(obj, 'pk', 'N/A')}")
                else:
                    try:
                        action = getattr(obj, 'action', str(obj))
                        due = getattr(obj, 'due_date', 'N/A')
                        risk_id = obj.risk.risk_id if getattr(obj, 'risk', None) else getattr(obj, 'risk_id', 'N/A')
                        status = getattr(obj, 'status', 'N/A')
                        lines.append(f" - {action} — due {due} (Risk: {risk_id}) [status: {status}]")
                    except Exception:
                        lines.append(f" - Mitigation id={getattr(obj, 'pk', 'N/A')}")
        return "\n".join(lines)

    parts = []
    parts.append(f"Notifications for: {user.get_full_name() or user.username} (<{user.email if user.email else 'no-email'}>)")
    parts.append(f"Generated at: {context['generated_at']}")
    if context.get('sample_text'):
        parts.append('\n' + context['sample_text'] + '\n')

    parts.append(_format_items_section('Assessments', context['assessment_items'], 'assessment'))
    if show_queries:
        parts.append('\nAssessment Queries:')
        parts.append(assessment_queries.get('pending') or 'pending: <no query>')
        parts.append(assessment_queries.get('upcoming') or 'upcoming: <no query>')
        parts.append(assessment_queries.get('overdue') or 'overdue: <no query>')
    parts.append('\n')
    parts.append(_format_items_section('Mitigations', context['mitigation_items'], 'mitigation'))
    if show_queries:
        parts.append('\nMitigation Queries:')
        parts.append(mitigation_queries.get('pending') or 'pending: <no query>')
        parts.append(mitigation_queries.get('upcoming') or 'upcoming: <no query>')
        parts.append(mitigation_queries.get('overdue') or 'overdue: <no query>')

    text_body = "\n\n".join(parts)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    to = [user.email] if user.email else []
    # For test sends, if the user has no email, use a sentinel test address
    if test and not to:
        to = ['test+{0}@example.local'.format(getattr(user, 'username', 'user'))]

    if not to:
        logger.warning('User %s has no email address; skipping notification', user)
        return 0

    msg = EmailMultiAlternatives(subject, text_body, from_email, to)
    msg.attach_alternative(html_body, 'text/html')

    # If a connection is provided (e.g. console backend for testing), use it.
    # Build an EmailMessage in the simple form so the console backend prints
    # a readable plain-text email (matches the example you supplied).
    if connection is not None:
        try:
            # Prepare recipients and optional bcc/reply_to
            bcc = []
            reply_to = []
            headers = {"Message-ID": "notif-{0}".format(getattr(user, 'pk', '0'))}

            # If the recipient list is empty (test), provide a sentinel test address
            if not to:
                to = ['test+{0}@example.local'.format(getattr(user, 'username', 'user'))]

            email_msg = EmailMessage(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=to,
                bcc=bcc,
                reply_to=reply_to,
                headers=headers,
            )

            # Send via provided connection (console backend will print)
            connection.send_messages([email_msg])
        except Exception:
            logger.exception('Failed to send notification via provided connection')
            return 0
    else:
        # Use the default configured email backend
        msg.send()

    logger.info('Sent notification email to %s (test=%s)', user.email, test)
    return 1


def notify_staff_of_outstanding_items(connection=None, include_details=True, upcoming_days=7):
    """Notify all staff/superusers with an aggregated summary of outstanding
    assessments and mitigations across the system. This excludes sending to
    individual risk owners.

    If `connection` is a console backend, the summary will be printed to stdout.
    """
    User = get_user_model()
    today = date.today()
    upcoming_cutoff = today + timedelta(days=upcoming_days)

    # Gather assessments: only immediate upcoming (within upcoming_days) and overdue
    upcoming_assess = PeriodicMeasurementSchedule.objects.filter(status='pending', scheduled_date__gte=today, scheduled_date__lte=upcoming_cutoff).select_related('indicator', 'indicator__risk', 'indicator__risk__risk_owner').order_by('scheduled_date')
    overdue_assess = PeriodicMeasurementSchedule.objects.filter(status='pending', scheduled_date__lt=today).select_related('indicator', 'indicator__risk', 'indicator__risk__risk_owner').order_by('scheduled_date')

    # Gather mitigations
    pending_mitig = Mitigation.objects.filter(status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person', 'risk__risk_owner').order_by('due_date')
    upcoming_mitig = Mitigation.objects.filter(due_date__gte=today, due_date__lte=upcoming_cutoff, status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person', 'risk__risk_owner').order_by('due_date')
    overdue_mitig = Mitigation.objects.filter(due_date__lt=today, status__in=['pending', 'in_progress']).select_related('risk', 'responsible_person', 'risk__risk_owner').order_by('due_date')

    # Helper to get owner key
    def owner_key_from_risk(risk):
        try:
            ro = getattr(risk, 'risk_owner', None)
            if ro and ro.name:
                return ro.name
        except Exception:
            pass
        return 'Unassigned'

    # Build grouped structure by owner
    grouped: Dict[str, Dict[str, List[str]]] = {}

    def add_line(owner, section, line):
        grouped.setdefault(owner, {}).setdefault(section, []).append(line)

    # Format assessments: only include upcoming and overdue
    for qs, label in ((upcoming_assess, f'Upcoming Assessments (next {upcoming_days} days)'), (overdue_assess, 'Overdue Assessments')):
        for item in qs:
            risk = getattr(item, 'indicator', None) and getattr(item.indicator, 'risk', None)
            owner = owner_key_from_risk(risk) if risk else 'Unassigned'
            kpi = getattr(item.indicator, 'preferred_kpi_name', getattr(item, 'indicator', str(item)))
            sched = getattr(item, 'scheduled_date', 'N/A')
            risk_id = risk.risk_id if risk else 'N/A'
            line = f"[{risk_id}] {kpi} - scheduled {sched}"
            add_line(owner, label, line)

    # Format mitigations: only include upcoming and overdue
    for qs, label in ((upcoming_mitig, f'Upcoming Mitigations (next {upcoming_days} days)'), (overdue_mitig, 'Overdue Mitigations')):
        for item in qs:
            risk = getattr(item, 'risk', None)
            owner = owner_key_from_risk(risk) if risk else 'Unassigned'
            action = getattr(item, 'action', str(item))
            due = getattr(item, 'due_date', 'N/A')
            status = getattr(item, 'status', 'N/A')
            risk_id = risk.risk_id if risk else 'N/A'
            line = f"[{risk_id}] {action} - due {due} (status={status})"
            add_line(owner, label, line)

    # Build text body
    lines: List[str] = []
    lines.append('Outstanding items summary')
    lines.append(f'Generated at: {datetime.now()}')
    lines.append('=' * 72)

    if not grouped:
        lines.append('No outstanding assessments or mitigations found.')
    else:
        for owner, sections in grouped.items():
            lines.append('\n' + owner)
            lines.append('-' * 40)
            for section_label, items in sections.items():
                lines.append(f'{section_label} ({len(items)}):')
                for it in items:
                    lines.append('  ' + it)

    body = '\n'.join(lines)

    # Recipients: all staff and superusers with emails
    staff_users = User.objects.filter(is_active=True).filter(models.Q(is_staff=True) | models.Q(is_superuser=True)).exclude(email__isnull=True).exclude(email__exact='')
    recipients = [u.email for u in staff_users]

    subject = 'Outstanding assessments & mitigations summary'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')

    if connection and isinstance(connection, DjangoConsoleEmailBackend):
        # Print human-readable summary to stdout
        print('=' * 72)
        print(body)
        print('=' * 72)
        return len(recipients)

    # Send real email
    if recipients:
        msg = EmailMultiAlternatives(subject, body, from_email, recipients)
        try:
            msg.send()
            logger.info('Sent staff aggregated outstanding items to %d recipients', len(recipients))
            return len(recipients)
        except Exception:
            logger.exception('Failed to send staff aggregated outstanding items')
            return 0
    else:
        logger.warning('No staff recipients with email found for outstanding items notification')
        return 0
