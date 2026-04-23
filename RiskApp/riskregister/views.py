
# Consolidate all imports at the very top
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.db.models import F, ExpressionWrapper, IntegerField, Count, Min, Case, When, Value, BooleanField, Q, Max, Avg
from django.core.exceptions import FieldError
import logging
from collections import defaultdict
from django.db.models import Prefetch
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
import re
# Import models
from .models import Risk, Mitigation, Control, RiskOwner, Department, RiskAssessment, NotificationPreference
from .utils.notifications import _gather_assessment_items_for_user, _gather_mitigation_items_for_user

# Risk Matrix View (for all risks)
@login_required
def risk_matrix(request):
    # Get all non-deleted risks
    risks = Risk.objects.filter(is_deleted=False)
    matrix_rows = []
    for risk in risks:
        # Use risk_id and title for display, match template JS
        score = risk.risk_score
        matrix_rows.append({
            'id': risk.risk_id,
            'name': risk.title,
            'score': score,
            'likelihood': risk.likelihood,
            'impact': risk.impact,
        })
    import json
    context = {
        'matrix_json': json.dumps(matrix_rows),
    }
    return render(request, 'riskregister/risk_matrix.html', context)

# Risk Owner Matrix View
@login_required
def risk_owner_matrix(request):
    # Ensure user is a risk owner
    if not hasattr(request.user, 'risk_owner_profile'):
        messages.error(request, 'Access denied. You are not registered as a risk owner.')
        return redirect('home')
    risk_owner = request.user.risk_owner_profile
    # Get all risks owned by this risk owner
    risks = Risk.objects.filter(risk_owner=risk_owner, is_deleted=False)
    # Prepare matrix_rows for Highcharts (risk_id, title, risk_score, likelihood, impact, rating class)
    matrix_rows = []
    for risk in risks:
        # Color class logic (match detail page)
        score = risk.risk_score
        if score >= 20:
            rating_class = 'bg-danger'
        elif score >= 15:
            rating_class = 'bg-danger'
        elif score >= 8:
            rating_class = 'bg-warning'
        else:
            rating_class = 'bg-success'
        matrix_rows.append({
            'risk_id': risk.risk_id,
            'title': risk.title,
            'score': score,
            'likelihood': risk.likelihood,
            'impact': risk.impact,
            'rating_class': rating_class,
        })
    context = {
        'matrix_json': json.dumps(matrix_rows),
        'risk_owner': risk_owner,
    }
    return render(request, 'riskregister/risk_owner_matrix.html', context)
logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
# Restricted risk detail view for risk owners
@login_required
def risk_owner_detailed(request, risk_id):
    # Only allow access if user is a risk owner and owns this risk
    if not hasattr(request.user, 'risk_owner_profile'):
        messages.error(request, 'Access denied. You are not registered as a risk owner.')
        return redirect('home')
    risk_owner = request.user.risk_owner_profile
    # Parse risk_id (e.g., R01IT)
    import re
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if not match:
        messages.error(request, 'Invalid risk ID format.')
        return redirect('risk_owner_dashboard')
    risk_number = int(match.group(1))
    dept_abbr = match.group(2)
    risk = get_object_or_404(Risk, risk_number=risk_number, department__abbreviation__iexact=dept_abbr, risk_owner=risk_owner)
    mitigations = Mitigation.objects.filter(risk=risk).select_related('responsible_person').order_by('due_date')
    controls = Control.objects.filter(risk_id=risk.pk, is_active=True).select_related('control_owner').order_by('-weight', 'control_type')
    risk_score = risk.risk_rating if risk else 0
    if risk_score >= 20:
        risk_priority = {'level': 'Critical', 'class': 'danger'}
    elif risk_score >= 15:
        risk_priority = {'level': 'High', 'class': 'danger'}
    elif risk_score >= 8:
        risk_priority = {'level': 'Medium', 'class': 'warning'}
    else:
        risk_priority = {'level': 'Low', 'class': 'success'}
    status = 'Draft' if (risk and risk.park_risk) else ('Approved' if (risk and risk.is_approved) else 'Pending Approval')
    # Residual risk calculation if available
    residual_risk_data = None
    if hasattr(risk, 'inherent_likelihood') and hasattr(risk, 'inherent_impact') and risk.inherent_likelihood and risk.inherent_impact:
        if hasattr(risk, 'calculate_residual_risk'):
            try:
                residual_risk_data = risk.calculate_residual_risk()
            except Exception:
                residual_risk_data = None

    # Assessments for this risk
    assessments = []
    try:
        from .models import RiskAssessment
        assessments = RiskAssessment.objects.filter(risk=risk).order_by('-assessment_date', '-created_at')
    except Exception:
        assessments = []

    # Mitigation stats
    total_mitigations = mitigations.count()
    completed_mitigations = mitigations.filter(status='complete').count()
    in_progress_mitigations = mitigations.filter(status='in_progress').count()
    pending_mitigations = mitigations.filter(status='pending').count()
    overdue_mitigations = sum(1 for m in mitigations if hasattr(m, 'is_overdue') and m.is_overdue)
    mitigation_progress = (completed_mitigations / total_mitigations * 100) if total_mitigations > 0 else 0

    context = {
        'risk': risk,
        'mitigations': mitigations,
        'controls': controls,
        'risk_score': risk_score,
        'risk_priority': risk_priority,
        'status': status,
        'residual_risk_data': residual_risk_data,
        'assessments': assessments,
        'total_mitigations': total_mitigations,
        'completed_mitigations': completed_mitigations,
        'in_progress_mitigations': in_progress_mitigations,
        'pending_mitigations': pending_mitigations,
        'overdue_mitigations': overdue_mitigations,
        'mitigation_progress': round(mitigation_progress, 1),
    }
    return render(request, 'riskregister/risk_owner_detailed.html', context)


@login_required
def risk_owner_assessment_history(request, risk_id):
    """List all risk assessments for a risk owned by the current risk owner."""
    if not hasattr(request.user, 'risk_owner_profile'):
        messages.error(request, 'Access denied. You are not registered as a risk owner.')
        return redirect('home')
    risk_owner = request.user.risk_owner_profile
    # parse risk_id similar to other owner views
    import re
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if not match:
        messages.error(request, 'Invalid risk ID format.')
        return redirect('risk_owner_dashboard')
    risk_number = int(match.group(1))
    dept_abbr = match.group(2)
    risk = get_object_or_404(Risk, risk_number=risk_number, department__abbreviation__iexact=dept_abbr, risk_owner=risk_owner)

    assessments = RiskAssessment.objects.filter(risk=risk).select_related('assessor').order_by('-assessment_date')

    context = {
        'risk': risk,
        'assessments': assessments,
        'page_title': f'Assessment History - {risk.risk_id}'
    }
    return render(request, 'riskregister/risk_owner_assessment_history.html', context)


@login_required
def risk_owner_mitigation_history(request, risk_id):
    """List mitigation items and progress logs for a risk owned by the current risk owner."""
    if not hasattr(request.user, 'risk_owner_profile'):
        messages.error(request, 'Access denied. You are not registered as a risk owner.')
        return redirect('home')
    risk_owner = request.user.risk_owner_profile
    import re
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if not match:
        messages.error(request, 'Invalid risk ID format.')
        return redirect('risk_owner_dashboard')
    risk_number = int(match.group(1))
    dept_abbr = match.group(2)
    risk = get_object_or_404(Risk, risk_number=risk_number, department__abbreviation__iexact=dept_abbr, risk_owner=risk_owner)

    mitigations = Mitigation.objects.filter(risk=risk).select_related('responsible_person').order_by('-due_date')
    # aggregate recent progress logs for these mitigations
    progress_logs = MitigationProgressLog.objects.filter(mitigation__in=mitigations).select_related('mitigation', 'user').order_by('-created_at')

    context = {
        'risk': risk,
        'mitigations': mitigations,
        'progress_logs': progress_logs,
        'page_title': f'Mitigation History - {risk.risk_id}'
    }
    return render(request, 'riskregister/risk_owner_mitigation_history.html', context)


@login_required
def mitigations_history(request):
    """Application page listing mitigation history and progress metrics."""
    status = request.GET.get('status')
    owner = request.GET.get('owner')
    overdue = request.GET.get('overdue')  # '1' to filter overdue
    selected_mitigation = request.GET.get('mitigation')

    qs = Mitigation.objects.select_related('risk', 'responsible_person').annotate(
        logs_count=Count('progress_logs'),
        last_update=Max('progress_logs__created_at')
    ).order_by('-last_update', '-updated_at')

    if status:
        qs = qs.filter(status__iexact=status)
    if owner:
        try:
            owner_id = int(owner)
            qs = qs.filter(responsible_person_id=owner_id)
        except Exception:
            pass
    if overdue == '1':
        from datetime import date
        qs = qs.filter(due_date__lt=date.today()).exclude(status__iexact='complete')

    # If a single mitigation id is provided, filter to it
    if selected_mitigation:
        try:
            mid = int(selected_mitigation)
            qs = qs.filter(pk=mid)
        except Exception:
            pass

    total = qs.count()

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(qs, 25)
    try:
        mitigations = paginator.page(page)
    except PageNotAnInteger:
        mitigations = paginator.page(1)
    except EmptyPage:
        mitigations = paginator.page(paginator.num_pages)

    owners = RiskOwner.objects.all().order_by('name')

    context = {
        'mitigations': mitigations,
        'total': total,
        'owners': owners,
        'selected_mitigation': selected_mitigation,
        'status_filter': status,
        'owner_filter': owner,
        'overdue_filter': overdue,
    }

    return render(request, 'riskregister/mitigations_history.html', context)
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.db.models import F, ExpressionWrapper, IntegerField, Count, Min, Case, When, Value, BooleanField, Q, Max, Avg
from django.core.exceptions import FieldError
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import RiskForm, RiskBasicInfoForm, RiskInherentAssessmentForm, RiskAssessmentForm, ManualRiskAssessmentForm, MitigationForm, ScheduleUpdateForm, IndicatorAssessmentForm, RiskIndicatorForm, RiskCategoryImpactFormSet, MitigationUpdateForm, ControlFormSet
from .models import Risk, Mitigation, MitigationProgressLog, Department, RiskCategory, KPI, RiskIndicator, IndicatorMeasurement, PeriodicMeasurementSchedule, IndicatorAssessment, RiskAssessment, ActivityLog, RiskCategoryImpact, Control, RiskOwner
from django.utils import timezone
import json
from django.utils.safestring import mark_safe
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime, date, timedelta
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from .utils.pdf_generator import generate_risk_report_pdf, generate_detailed_risk_report_pdf


def tasks(request):
    """Tasks overview page showing outstanding assessments, outstanding mitigations,
    and a department risk register. Filters: department, owner, and q (search).
    """
    q = request.GET.get('q', '').strip()
    department_id = request.GET.get('department')
    owner_id = request.GET.get('owner')
    department = None
    owner = None
    if department_id:
        try:
            department = Department.objects.get(pk=int(department_id))
        except (Department.DoesNotExist, ValueError, TypeError):
            department = None
    if owner_id:
        try:
            owner = RiskOwner.objects.get(pk=int(owner_id))
        except (RiskOwner.DoesNotExist, ValueError, TypeError):
            owner = None

    # Outstanding risk assessments: current assessments not completed/approved
    assessments_qs = RiskAssessment.objects.filter(is_current=True).exclude(status__in=['completed', 'approved'])
    if department:
        assessments_qs = assessments_qs.filter(risk__department=department)
    if owner:
        assessments_qs = assessments_qs.filter(risk__risk_owner=owner)
    if q:
        assessments_qs = assessments_qs.filter(
            Q(risk__title__icontains=q) | Q(risk__risk_number__icontains=q) | Q(risk__description__icontains=q)
        )
    assessments = assessments_qs.select_related('risk', 'assessor').order_by('assessment_date')

    # Upcoming assessments: assessments scheduled for the next 30 days
    from datetime import timedelta
    today = date.today()
    upcoming_date = today + timedelta(days=30)
    upcoming_assessments_qs = RiskAssessment.objects.filter(
        assessment_date__range=[today, upcoming_date],
        status__in=['draft', 'in_progress']
    )
    if department:
        upcoming_assessments_qs = upcoming_assessments_qs.filter(risk__department=department)
    if owner:
        upcoming_assessments_qs = upcoming_assessments_qs.filter(risk__risk_owner=owner)
    if q:
        upcoming_assessments_qs = upcoming_assessments_qs.filter(
            Q(risk__title__icontains=q) | Q(risk__risk_number__icontains=q) | Q(risk__description__icontains=q)
        )
    upcoming_assessments = upcoming_assessments_qs.select_related('risk', 'assessor').order_by('assessment_date')

    # Outstanding mitigations: not complete and not cancelled
    mitigations_qs = Mitigation.objects.exclude(status__in=['complete', 'cancelled'])
    if department:
        mitigations_qs = mitigations_qs.filter(risk__department=department)
    if owner:
        mitigations_qs = mitigations_qs.filter(risk__risk_owner=owner)
    if q:
        mitigations_qs = mitigations_qs.filter(
            Q(risk__title__icontains=q) | Q(action__icontains=q) | Q(responsible_person__name__icontains=q)
        )
    mitigations = mitigations_qs.select_related('risk', 'responsible_person').order_by('due_date')
    overdue_mitigations = mitigations_qs.filter(due_date__lt=today)

    # Department risk register
    risks_qs = Risk.objects.filter(is_deleted=False)
    if department:
        risks_qs = risks_qs.filter(department=department)
    if owner:
        risks_qs = risks_qs.filter(risk_owner=owner)
    if q:
        risks_qs = risks_qs.filter(Q(title__icontains=q) | Q(risk_number__icontains=q) | Q(description__icontains=q))
    risks = risks_qs.select_related('department', 'category', 'risk_owner').order_by('risk_number')

    departments = Department.objects.all().order_by('name')
    owners = RiskOwner.objects.all().order_by('name')

    context = {
        'assessments': assessments,
        'upcoming_assessments': upcoming_assessments,
        'mitigations': mitigations,
        'overdue_mitigations': overdue_mitigations,
        'risks': risks,
        'departments': departments,
        'owners': owners,
        'selected_department': department,
        'selected_owner': owner,
        'q': q,
    }

    return render(request, 'riskregister/tasks.html', context)


@login_required
def risk_owner_dashboard(request):
    """Risk Owner restricted dashboard showing only their owned risks and related tasks."""
    # Check if user is a risk owner - improved method with direct user relationship
    risk_owner = None
    """Risk Owner restricted dashboard showing only their owned risks and related tasks."""
    # Check if user is a risk owner - improved method with direct user relationship
    risk_owner = None
    
    # First try direct user relationship
    if hasattr(request.user, 'risk_owner_profile'):
        risk_owner = request.user.risk_owner_profile
    else:
        # Fallback to email/name matching for existing data
        try:
            risk_owner = RiskOwner.objects.get(
                Q(email__iexact=request.user.email) | Q(name__icontains=request.user.get_full_name())
            )
            # Link the user to risk owner for future logins
            if risk_owner and not risk_owner.user:
                risk_owner.user = request.user
                risk_owner.save()
        except RiskOwner.DoesNotExist:
            pass
    
    if not risk_owner:
        messages.error(request, 'Access denied. You are not registered as a risk owner.')
        return redirect('home')

    q = request.GET.get('q', '').strip()

    # Get risks owned by this risk owner
    owned_risks_qs = Risk.objects.filter(risk_owner=risk_owner, is_deleted=False)
    if q:
        owned_risks_qs = owned_risks_qs.filter(Q(title__icontains=q) | Q(risk_number__icontains=q) | Q(description__icontains=q))
    owned_risks = owned_risks_qs.select_related('department', 'category').order_by('risk_number')

    # Get assessments for owned risks
    assessments_qs = RiskAssessment.objects.filter(
        risk__risk_owner=risk_owner,
        is_current=True
    ).exclude(status__in=['completed', 'approved'])
    if q:
        assessments_qs = assessments_qs.filter(Q(risk__title__icontains=q) | Q(risk__risk_number__icontains=q))
    assessments = assessments_qs.select_related('risk', 'assessor').order_by('assessment_date')

    # Get upcoming assessments for owned risks
    from datetime import timedelta
    today = date.today()
    upcoming_date = today + timedelta(days=30)
    upcoming_assessments_qs = RiskAssessment.objects.filter(
        risk__risk_owner=risk_owner,
        assessment_date__range=[today, upcoming_date],
        status__in=['draft', 'in_progress']
    )
    if q:
        upcoming_assessments_qs = upcoming_assessments_qs.filter(Q(risk__title__icontains=q) | Q(risk__risk_number__icontains=q))
    upcoming_assessments = upcoming_assessments_qs.select_related('risk', 'assessor').order_by('assessment_date')

    # Get mitigations assigned to this risk owner or for their risks
    mitigations_qs = Mitigation.objects.filter(
        Q(responsible_person=risk_owner) | Q(risk__risk_owner=risk_owner)
    ).exclude(status__in=['complete', 'cancelled'])
    if q:
        mitigations_qs = mitigations_qs.filter(
            Q(risk__title__icontains=q) | Q(action__icontains=q)
        )
    mitigations = mitigations_qs.select_related('risk', 'responsible_person').order_by('due_date')
    overdue_mitigations = mitigations_qs.filter(due_date__lt=today)

    # Get controls owned by this risk owner
    owned_controls_qs = Control.objects.filter(control_owner=risk_owner, is_active=True)
    if q:
        owned_controls_qs = owned_controls_qs.filter(
            Q(risk__title__icontains=q) | Q(description__icontains=q) | Q(control_type__icontains=q)
        )
    owned_controls = owned_controls_qs.select_related('risk').order_by('-effectiveness')

    context = {
        'risk_owner': risk_owner,
        'owned_risks': owned_risks,
        'assessments': assessments,
        'upcoming_assessments': upcoming_assessments,
        'mitigations': mitigations,
        'overdue_mitigations': overdue_mitigations,
        'owned_controls': owned_controls,
        'q': q,
    }

    # Provide explicit counts for use in templates (avoids calling QuerySet.count in templates)
    context.update({
        'owned_risks_count': owned_risks.count(),
        'upcoming_assessments_count': upcoming_assessments.count(),
        'mitigations_count': mitigations.count(),
        'overdue_mitigations_count': overdue_mitigations.count(),
        'owned_controls_count': owned_controls.count(),
    })

    return render(request, 'riskregister/risk_owner_dashboard.html', context)


# Simple JSON endpoint returning unread notification count (0 or 1).
# We treat any outstanding items (pending/upcoming/overdue assessments or
# mitigations) as a single unread notification indicator for the UI.
def notifications_unread_count(request):
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})

    # Determine preference (use defaults if none)
    try:
        pref = request.user.notification_preference
    except Exception:
        pref = None

    # Gather items using helper functions
    user = request.user
    try:
        assess_items, _ = _gather_assessment_items_for_user(user, pref if pref else NotificationPreference(user=user))
        mitig_items, _ = _gather_mitigation_items_for_user(user, pref if pref else NotificationPreference(user=user))
    except Exception:
        return JsonResponse({'unread_count': 0})

    has_items = any(len(v) for v in assess_items.values()) or any(len(v) for v in mitig_items.values())
    return JsonResponse({'unread_count': 1 if has_items else 0})


@login_required
def notification_center(request):
    """Minimal notifications center: show gathered assessment and mitigation items."""
    try:
        pref = request.user.notification_preference
    except Exception:
        pref = None

    try:
        assess_items, assess_counts = _gather_assessment_items_for_user(request.user, pref if pref else NotificationPreference(user=request.user))
        mitig_items, mitig_counts = _gather_mitigation_items_for_user(request.user, pref if pref else NotificationPreference(user=request.user))
    except Exception:
        assess_items, mitig_items = {}, {}

    context = {
        'assess_items': assess_items,
        'mitig_items': mitig_items,
    }
    return render(request, 'riskregister/notification_center.html', context)

# Helper function to check if user is superuser
def is_superuser(user):
    return user.is_superuser


def auto_generate_risk_assessment_from_indicators(risk, assessor=None):
    """
    Automatically generate or update a risk assessment based on all indicator assessments.
    This is triggered after indicator assessments are recorded.
    
    Returns: (assessment, created) tuple
    """
    from django.db.models import Avg, Count
    
    # Get all recent indicator assessments for this risk
    indicator_assessments = IndicatorAssessment.objects.filter(
        indicator__risk_id=risk.pk,
        is_current=True
    ).select_related('indicator')
    
    if not indicator_assessments.exists():
        return None, False
    
    # Get the latest assessment date
    latest_assessment_date = indicator_assessments.latest('assessment_date').assessment_date
    
    # Calculate aggregate status from indicator assessments
    status_counts = indicator_assessments.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}
    
    breached = status_dict.get('breached', 0)
    caution = status_dict.get('caution', 0)
    on_target = status_dict.get('on_target', 0)
    
    # Determine overall risk level based on indicator results
    # If any indicator is breached, risk is high
    # If any indicator is caution, risk is medium
    # Otherwise, risk is low
    if breached > 0:
        likelihood = 5
        impact = 5
    elif caution > 0:
        likelihood = 3
        impact = 3
    else:
        likelihood = 2
        impact = 2
    
    # Get or create current assessment
    assessment, created = RiskAssessment.objects.get_or_create(
        risk=risk,
        assessment_date=latest_assessment_date,
        defaults={
            'assessment_type': 'periodic',
            'likelihood': likelihood,
            'impact': impact,
            'assessor': assessor,
            'status': 'completed',
            'is_current': True,
        }
    )
    
    if not created:
        # Update existing assessment
        assessment.likelihood = likelihood
        assessment.impact = impact
        assessment.status = 'completed'
        assessment.is_current = True
        assessment.save()
    
    # Link indicator assessments
    assessment.source_indicator_assessments.set(indicator_assessments)
    
    # Update risk likelihood and impact
    risk.likelihood = likelihood
    risk.impact = impact
    risk.save(update_fields=['likelihood', 'impact'])
    return assessment, True


# Authentication Views
def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        # Check if user is a risk owner and redirect accordingly
        if hasattr(request.user, 'risk_owner_profile') and request.user.risk_owner_profile:
            return redirect('risk_owner_dashboard')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Check if user is a risk owner and redirect accordingly
            if hasattr(user, 'risk_owner_profile') and user.risk_owner_profile:
                return redirect('risk_owner_dashboard')
            
            # Redirect to next parameter or home for regular users
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'riskregister/login.html')


def logout_view(request):
    """Handle user logout"""
    auth_logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')


@login_required
def post_login_redirect(request):
    """Central redirect target after any login flow.

    Ensures users who are linked to a `RiskOwner` are always sent to the
    `risk_owner_dashboard`, while other users go to the regular `dashboard`.
    This view is referenced by `LOGIN_REDIRECT_URL` so all auth flows converge
    on the same logic.
    """
    user = request.user
    try:
        # Accessing the reverse one-to-one will raise RiskOwner.DoesNotExist
        # if no related RiskOwner exists; use a try/except to be explicit.
        if hasattr(user, 'risk_owner_profile') and user.risk_owner_profile:
            return redirect('risk_owner_dashboard')
    except Exception:
        # Any issues resolving the relation should not block login redirect.
        pass
        return redirect('home')


@login_required
@login_required
def index(request):
    return redirect('home')

@login_required
def create_risk(request):
    """
    Multi-stage risk creation workflow:
    Stage 1: Basic risk information
    Stage 2: Inherent risk assessment and internal controls
    Stage 3: View residual risk rating
    """
    stage = request.GET.get('stage', '1')
    risk_id = request.session.get('draft_risk_id')
    
    # Stage 1: Basic Information
    if stage == '1':
        if request.method == 'POST':
            risk_form = RiskBasicInfoForm(request.POST)
            category_formset = RiskCategoryImpactFormSet(request.POST)
            
            if risk_form.is_valid() and category_formset.is_valid():
                # Save risk as draft
                risk = risk_form.save(commit=False)
                risk.created_by = request.user
                risk.status = 'draft'  # Mark as draft until stage 3 complete
                risk.park_risk = True
                
                # Set default values for required fields (will be updated in stage 2)
                if not risk.likelihood:
                    risk.likelihood = 3
                if not risk.impact:
                    risk.impact = 3
                if not risk.inherent_likelihood:
                    risk.inherent_likelihood = 3
                if not risk.inherent_impact:
                    risk.inherent_impact = 3
                
                risk.save()
                
                # Save additional category impacts
                try:
                    category_formset.instance = risk
                    category_formset.save()
                except Exception as e:
                    logger.exception("Error saving category impacts: %s", e)
                
                # Store risk ID in session for stage 2
                request.session['draft_risk_id'] = risk.pk
                
                messages.success(request, f'Risk "{risk.title}" basic information saved! Now complete inherent risk assessment and controls.')
                
                # Redirect to stage 2
                return redirect(f"{request.path}?stage=2")
            else:
                logger.debug("Risk form errors: %s", risk_form.errors)
                try:
                    logger.debug("Category formset errors: %s", category_formset.errors)
                except Exception:
                    pass
        else:
            risk_form = RiskBasicInfoForm()
            category_formset = RiskCategoryImpactFormSet()
        
        kpis = KPI.objects.all().order_by('name')
        
        return render(request, 'risk_form_stage1.html', {
            'risk_form': risk_form,
            'category_formset': category_formset,
            'kpis': kpis,
            'stage': 1,
            'total_stages': 4,
        })
    
    # Stage 2: Inherent Assessment and Controls
    elif stage == '2':
        if not risk_id:
            messages.error(request, 'Please complete Stage 1 first.')
            return redirect('create_risk')
        
        try:
            risk = Risk.objects.get(pk=risk_id, created_by=request.user)
        except Risk.DoesNotExist:
            messages.error(request, 'Risk not found. Please start over.')
            del request.session['draft_risk_id']
            return redirect('create_risk')
        
        if request.method == 'POST':
            assessment_form = RiskInherentAssessmentForm(request.POST, instance=risk)
            control_formset = ControlFormSet(request.POST, instance=risk, prefix='controls')
            
            if assessment_form.is_valid() and control_formset.is_valid():
                # Save inherent assessment
                risk = assessment_form.save(commit=False)
                risk.save()
                
                # Save controls
                try:
                    controls = control_formset.save(commit=False)
                    for control in controls:
                        control.risk = risk
                        if not control.created_by:
                            control.created_by = request.user
                        control.save()
                    control_formset.save_m2m()
                    
                    # Handle deleted controls
                    for deleted_control in control_formset.deleted_objects:
                        deleted_control.delete()
                except Exception as e:
                    logger.exception("Error saving controls: %s", e)
                
                messages.success(request, f'Inherent assessment and controls saved! Review residual risk rating.')
                
                # Redirect to stage 3 (residual risk view)
                return redirect(f"{request.path}?stage=3")
            else:
                logger.debug("Assessment form errors: %s", assessment_form.errors)
                logger.debug("Control formset errors: %s", control_formset.errors)
        else:
            assessment_form = RiskInherentAssessmentForm(instance=risk)
            control_formset = ControlFormSet(instance=risk, prefix='controls', queryset=Control.objects.none())
        
        return render(request, 'risk_form_stage2.html', {
            'risk': risk,
            'assessment_form': assessment_form,
            'control_formset': control_formset,
            'stage': 2,
            'total_stages': 4,
        })
    
    # Stage 3: Residual Risk Rating
    elif stage == '3':
        if not risk_id:
            messages.error(request, 'Please complete previous stages first.')
            return redirect('create_risk')
        
        try:
            risk = Risk.objects.get(pk=risk_id, created_by=request.user)
        except Risk.DoesNotExist:
            messages.error(request, 'Risk not found. Please start over.')
            if 'draft_risk_id' in request.session:
                del request.session['draft_risk_id']
            return redirect('create_risk')
        
        if request.method == 'POST':
            # Handle status based on action button clicked
            action = request.POST.get('action', 'park')
            if action == 'submit':
                risk.status = 'pending'
                risk.park_risk = False
            else:  # park or default
                risk.status = 'parked'
                risk.park_risk = True
            
            risk.save()
            
            # Clear draft session
            if 'draft_risk_id' in request.session:
                del request.session['draft_risk_id']
            
            # Store risk ID for indicator workflow
            request.session['new_risk_id'] = risk.pk
            request.session['workflow_step'] = 'add_indicators'
            
            messages.success(request, f'Risk "{risk.title}" created successfully! Now add risk indicators.')
            
            # Redirect to add indicators page
            return redirect('add_indicator', risk_id=risk.pk)
        
        # Calculate residual risk
        residual_data = risk.calculate_residual_risk()
        controls = risk.controls.filter(is_active=True).order_by('-weight', 'control_type')
        
        return render(request, 'risk_form_stage3.html', {
            'risk': risk,
            'residual_data': residual_data,
            'controls': controls,
            'stage': 3,
            'total_stages': 4,
        })
    
    else:
        messages.error(request, 'Invalid stage.')
        return redirect('create_risk')


@login_required
def dashboard(request):
    today = date.today()
    fifteen_days = today + timedelta(days=15)
    ninety_days_ago = today - timedelta(days=90)
    
    # Base queryset
    qs = Risk.objects.select_related('department', 'risk_owner', 'category').annotate(
        score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
    )
    
    # Role-based filtering
    user = request.user
    if user.is_superuser:
        # Superuser sees all risks (show all statuses for backward compatibility)
        approved_risks = qs.filter(status='approved')
        pending_risks = qs.filter(status='pending')
        parked_risks = qs.filter(status='parked')
        rejected_risks = qs.filter(status='rejected')
    else:
        # Staff users see only approved risks (read-only) and their own parked/pending risks
        approved_risks = qs.filter(status='approved')
        pending_risks = qs.filter(status='pending', created_by=user)
        parked_risks = qs.filter(status='parked', created_by=user)
        rejected_risks = qs.filter(status='rejected', created_by=user)
    
    high_qs = approved_risks.filter(score__gte=15).order_by('-score')[:50]
    high_count = approved_risks.filter(score__gte=15).count()

    # total mitigations recorded
    total_mitigations = Mitigation.objects.count()

    # risks without mitigations
    risks_without_mitigations = Risk.objects.annotate(m_count=Count('mitigations')).filter(m_count=0).count()

    # Provide actual Risk queryset/list to the template so attributes like
    # `risk_id`, `score`, `created_by`, and `created_at` are available.
    # `high_qs` is already based on `qs` which was select_related/annotated,
    # so pass it directly.
    high_risks = list(high_qs)
    
    # NEW: Calculate inherent vs residual risk statistics
    risks_with_inherent = approved_risks.filter(
        inherent_likelihood__isnull=False,
        inherent_impact__isnull=False
    )
    total_risks_with_inherent = risks_with_inherent.count()
    
    # Calculate average risk reduction from controls
    total_reduction = 0
    risks_with_reduction = 0
    avg_control_effectiveness = 0
    total_controls = 0
    
    for risk in risks_with_inherent:
        residual_data = risk.calculate_residual_risk()
        if residual_data.get('risk_reduction_pct', 0) > 0:
            total_reduction += residual_data['risk_reduction_pct']
            risks_with_reduction += 1
        if residual_data.get('control_effectiveness', 0) > 0:
            avg_control_effectiveness += residual_data['control_effectiveness']
    
    # Calculate averages
    avg_risk_reduction = round(total_reduction / risks_with_reduction, 1) if risks_with_reduction > 0 else 0
    avg_control_effectiveness = round(avg_control_effectiveness / risks_with_reduction, 1) if risks_with_reduction > 0 else 0
    
    # Get total active controls
    from .models import Control
    total_controls = Control.objects.filter(is_active=True).count()
    
    # Control type distribution
    control_types = Control.objects.filter(is_active=True).values('control_type').annotate(
        count=Count('id'),
        avg_effectiveness=Avg('effectiveness')
    )
    
    # Get high risks with inherent data for detailed display
    high_risks_with_inherent = []
    for risk in high_risks:
        if risk.inherent_likelihood and risk.inherent_impact:
            residual_data = risk.calculate_residual_risk()
            risk.residual_data = residual_data
            risk.has_inherent = True
            high_risks_with_inherent.append(risk)
        else:
            risk.has_inherent = False

    # Total risks shown on dashboard should reflect approved risks only
    total_risks = Risk.objects.filter(status='approved').count()

    # aggregate counts by category
    category_counts = (
        Risk.objects.filter(status='approved')
            .values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
    )

    # Compute weighted aggregated risk scores using category importance (1-10)
    from .models import RiskCategory
    category_weighted_stats = []
    weighted_numerator = 0.0
    weighted_denominator = 0.0

    categories = RiskCategory.objects.all()
    for cat in categories:
        cat_qs = approved_risks.filter(category=cat)
        cat_count = cat_qs.count()
        if cat_count == 0:
            total_score = 0
            avg_score = 0.0
        else:
            # sum risk_score for risks in this category
            total_score = sum(getattr(r, 'risk_score', 0) for r in cat_qs)
            avg_score = float(total_score) / cat_count if cat_count > 0 else 0.0

        # Category importance weight (1-10). Normalize weighted score to 0-25 by dividing weight by 10
        cat_weight = float(getattr(cat, 'weight', 5) or 5)
        cat_weighted_score = avg_score * (cat_weight / 10.0)  # normalized to 0-25 scale

        # Accumulate for overall weighted average: use avg_score * count * weight
        weighted_numerator += avg_score * cat_count * cat_weight
        weighted_denominator += cat_count * cat_weight

        category_weighted_stats.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'count': cat_count,
            'total_score': total_score,
            'average_score': round(avg_score, 2),
            'weight': int(cat_weight),
            'weighted_score': round(cat_weighted_score, 2),
            'avg_pct': round((avg_score / 25.0) * 100, 2) if 25.0 > 0 else 0.0,
            'weighted_pct': round((cat_weighted_score / 25.0) * 100, 2) if 25.0 > 0 else 0.0,
        })

    overall_weighted_average = round((weighted_numerator / weighted_denominator), 2) if weighted_denominator > 0 else 0.0
    overall_weighted_total = round(overall_weighted_average * total_risks, 2) if total_risks > 0 else 0.0

    # NEW: Risks by Department and Severity for Stacked Histogram
    risks_by_dept_severity = {}
    departments = Department.objects.all()
    
    for dept in departments:
        dept_risks = qs.filter(department=dept, status='approved')
        risks_by_dept_severity[dept.name] = {
            'low': dept_risks.filter(score__gte=1, score__lte=7).count(),
            'medium': dept_risks.filter(score__gte=8, score__lte=14).count(),
            'high': dept_risks.filter(score__gte=15, score__lte=19).count(),
            'critical': dept_risks.filter(score__gte=20, score__lte=25).count(),
        }
    
    # Convert to JSON for JavaScript
    import json
    risks_by_dept_severity_json = json.dumps(risks_by_dept_severity)

    # annotate each Risk with the next (earliest) mitigation due date
    risks_with_due = (
        Risk.objects
            .annotate(next_mitigation_due=Min('mitigations__due_date'))
            .annotate(
                is_overdue=Case(
                    When(next_mitigation_due__lt=timezone.now().date(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )
    )

    # all risks that have a mitigation due (ordered by due date)
    risks_due_list = risks_with_due.filter(next_mitigation_due__isnull=False).order_by('next_mitigation_due')

    # NEW: Overdue mitigations
    overdue_mitigations = Mitigation.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'in_progress']
    ).select_related('risk', 'risk__department').order_by('due_date')[:10]
    
    # Calculate days overdue for each mitigation as a dictionary
    overdue_days_map = {}
    for mitigation in overdue_mitigations:
        if mitigation.due_date:
            overdue_days_map[mitigation.pk] = (today - mitigation.due_date).days
        else:
            overdue_days_map[mitigation.pk] = 0
    
    # NEW: Risks without any assessments
    risks_no_assessment = Risk.objects.filter(
        assessments__isnull=True
    ).select_related('department', 'risk_owner')[:10]
    
    # NEW: Assessments due in next 15 days
    assessments_due_soon = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__gte=today,
        scheduled_date__lte=fifteen_days,
        status='pending'
    ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')[:10]
    
    # NEW: Breached indicators (latest measurements)
    breached_indicators = IndicatorMeasurement.objects.filter(
        measured_at__gte=ninety_days_ago
    ).select_related('indicator', 'indicator__risk').order_by('-measured_at')
    
    # Filter only breached ones
    breached_list = []
    for measurement in breached_indicators:
        if measurement.indicator.evaluate(measurement.value) == 'breached':
            breached_list.append(measurement)
            if len(breached_list) >= 10:
                break
    
    # NEW: Risks needing review (last assessment > 90 days ago or never assessed)
    risks_with_old_assessments = Risk.objects.annotate(
        last_assessment=Max('assessments__assessment_date')
    ).filter(
        Q(last_assessment__lt=ninety_days_ago) | Q(last_assessment__isnull=True)
    ).select_related('department')[:10]
    
    # Add last assessment date for display
    risk_assessment_dates = {}
    for risk in risks_with_old_assessments:
        try:
            from .models import RiskAssessment
            latest = RiskAssessment.objects.filter(risk_id=risk.pk).order_by('-assessment_date').first()
            risk_assessment_dates[risk.pk] = latest.assessment_date if latest else 'Never'
        except (ImportError, Exception):
            risk_assessment_dates[risk.pk] = None
    
    context = {
        'total_risks': total_risks,
        'high_count': high_count,
        'total_mitigations': total_mitigations,
        'risks_without_mitigations': risks_without_mitigations,
        'category_counts': category_counts,
        'high_risks': high_risks,
        
        # Role-based risk lists
        'approved_risks': approved_risks,
        'pending_risks': pending_risks,
        'parked_risks': parked_risks,
        'approved_count': approved_risks.count(),
        'pending_count': pending_risks.count(),
        'parked_count': parked_risks.count(),
        'rejected_count': rejected_risks.count(),
        
        # New action items
        'overdue_mitigations': overdue_mitigations,
        'overdue_days_map': overdue_days_map,
        'risks_no_assessment': risks_no_assessment,
        'assessments_due_soon': assessments_due_soon,
        'breached_indicators': breached_list,
        'upcoming_reviews': risks_with_old_assessments,
        'risk_assessment_dates': risk_assessment_dates,
        
        # NEW: Inherent vs Residual Risk Data
        'total_risks_with_inherent': total_risks_with_inherent,
        'avg_risk_reduction': avg_risk_reduction,
        'avg_control_effectiveness': avg_control_effectiveness,
        'total_controls': total_controls,
        'control_types': control_types,
        'high_risks_with_inherent': high_risks_with_inherent,
        
        # NEW: Stacked histogram data
        'risks_by_dept_severity': risks_by_dept_severity_json,
        # Weighted risk metrics
        'category_weighted_stats': category_weighted_stats,
        'overall_weighted_average': overall_weighted_average,
        'overall_weighted_total': overall_weighted_total,
    }
    
    return render(request, 'Dashboard.html', context)


@login_required
def debug_risks_by_dept(request):
    """Debug endpoint: returns the risks-by-department severity JSON used by the dashboard."""
    from django.http import JsonResponse
    from django.db.models import F, ExpressionWrapper, IntegerField

    qs = Risk.objects.select_related('department').annotate(
        score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
    )

    result = {}
    for dept in Department.objects.all():
        dept_qs = qs.filter(department=dept, status='approved')
        result[dept.name] = {
            'low': dept_qs.filter(score__gte=1, score__lte=7).count(),
            'medium': dept_qs.filter(score__gte=8, score__lte=14).count(),
            'high': dept_qs.filter(score__gte=15, score__lte=19).count(),
            'critical': dept_qs.filter(score__gte=20, score__lte=25).count(),
        }

    return JsonResponse(result)

@login_required
def all_risks(request):
    # Only include approved risks (Risk.objects manager already hides soft-deleted records)
    qs = (
        Risk.objects.filter(status='approved')
            .select_related('department', 'category', 'risk_owner')
            .annotate(score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField()))
            .annotate(next_mitigation_due=Min('mitigations__due_date'))
            .order_by('-score', 'department__name', 'risk_number')
    )

    risks_list = []
    for r in qs:
        risks_list.append({
            'id': r.pk,
            'risk_id': r.risk_id if hasattr(r, 'risk_id') else str(r.pk),
            'title': r.title,
            'description': r.description or '',
            'department': r.department.name if r.department else '',
            'category': r.category.name if r.category else '',
            'owner': r.risk_owner.name if r.risk_owner else 'Unassigned',
            'priority': 'high' if (getattr(r, 'score', 0) or 0) >= 15 else ('medium' if (getattr(r, 'score', 0) or 0) >= 8 else 'low'),
            'status': 'open',
            'dueDate': getattr(r, 'next_mitigation_due').isoformat() if getattr(r, 'next_mitigation_due', None) else None,
            'dateIdentified': None,
            'likelihood': r.likelihood,
            'impact': r.impact,
            'mitigationPlan': '',
            'riskScore': getattr(r, 'score', 0) or 0,
        })

    # Get unique values for dropdowns from the database
    departments = Department.objects.all().values_list('name', flat=True).distinct().order_by('name')
    categories = RiskCategory.objects.all().values_list('name', flat=True).distinct().order_by('name')
    
    # Get unique owners from risks
    owners = Risk.objects.filter(status='approved').select_related('risk_owner').exclude(risk_owner__isnull=True).values_list('risk_owner__name', flat=True).distinct().order_by('risk_owner__name')

    context = {
        'risks_json': mark_safe(json.dumps(risks_list)),
        'risks_count': len(risks_list),
        'departments': list(departments),
        'categories': list(categories),
        'owners': list(owners),
    }
    return render(request, 'riskregister/Viewall2.html', context)


@login_required
def risk_view(request, risk_id):
    """
    Function-based view for displaying risk details
    """
    from django.http import Http404
    
    # Parse risk_id format: R{number}{DEPT_CODE} (e.g., R01HR, R02FN)
    # Also handle legacy numeric IDs for backwards compatibility
    risk = None
    
    logger.debug(f"DEBUG: Attempting to load risk with ID: {risk_id}")
    
    # Try parsing as formatted risk_id (e.g., R01HR)
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if match:
        risk_number = int(match.group(1))
        dept_abbr = match.group(2)
        logger.debug(f"DEBUG: Parsed as formatted ID - Number: {risk_number}, Dept: {dept_abbr}")
        try:
            risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').get(
                risk_number=risk_number,
                department__abbreviation__iexact=dept_abbr
            )
            logger.debug(f"DEBUG: Found risk: {risk.risk_id}")
        except Risk.DoesNotExist:
            logger.debug(f"DEBUG: No risk found with number {risk_number} and dept {dept_abbr}")
            return render(request, '404.html', {'message': f'Risk {risk_id} not found'}, status=404)
        except Risk.MultipleObjectsReturned:
            # Shouldn't happen but take the first match
            risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').filter(
                risk_number=risk_number,
                department__abbreviation__iexact=dept_abbr
            ).first()
            logger.debug(f"DEBUG: Multiple risks found, using first: {risk.risk_id}")
    else:
        logger.debug(f"DEBUG: Does not match formatted pattern, trying numeric lookup")
        # Fallback: try as numeric pk for backwards compatibility
        numbers = re.findall(r'\d+', str(risk_id))
        if numbers:
            numeric_id = int(numbers[0])
            logger.debug(f"DEBUG: Trying numeric ID: {numeric_id}")
            try:
                risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').get(pk=numeric_id)
                logger.debug(f"DEBUG: Found risk by numeric ID: {risk.risk_id}")
            except Risk.DoesNotExist:
                logger.debug(f"DEBUG: No risk found with pk={numeric_id}")
                return render(request, '404.html', {'message': f'Risk not found'}, status=404)
        else:
            logger.debug(f"DEBUG: Invalid risk ID format: {risk_id}")
            return render(request, '404.html', {'message': 'Invalid risk ID format'}, status=404)
    
    # Get mitigations for this risk
    mitigations = Mitigation.objects.filter(risk=risk).select_related('responsible_person').order_by('due_date')
    logger.debug(f"DEBUG: Found {mitigations.count()} mitigations for risk {risk.risk_id}")
    
    # Get controls for this risk
    controls = Control.objects.filter(risk_id=risk.pk, is_active=True).select_related('control_owner').order_by('-weight', 'control_type')
    
    # Calculate control type distribution
    control_distribution = {
        'preventive': sum(1 for c in controls if c.control_type == 'preventive'),
        'detective': sum(1 for c in controls if c.control_type == 'detective'),
        'corrective': sum(1 for c in controls if c.control_type == 'corrective'),
        'directive': sum(1 for c in controls if c.control_type == 'directive'),
    }
    
    # Calculate residual risk if inherent risk is set
    residual_risk_data = None
    if risk.inherent_likelihood and risk.inherent_impact:
        residual_risk_data = risk.calculate_residual_risk()
    
    # Get indicators for this risk - with error handling for invalid decimal data
    try:
        indicators_qs = RiskIndicator.objects.filter(risk_id=risk.pk, active=True).select_related('preferred_kpi').order_by('-created_at')
        indicators = list(indicators_qs)
    except Exception as e:
        logger.debug(f"Error loading indicators: {e}")
        indicators = []

    # Batch-load recent measurements for all indicators in one query to avoid N+1
    indicator_measurements = {}
    if indicators:
        try:
            indicator_ids = [i.pk for i in indicators]
            measurements_qs = IndicatorMeasurement.objects.filter(indicator_id__in=indicator_ids).order_by('-measured_at')
            from collections import defaultdict
            temp = defaultdict(list)
            for m in measurements_qs:
                if len(temp[m.indicator_id]) < 10:
                    temp[m.indicator_id].append(m)
            for i in indicators:
                indicator_measurements[i.pk] = temp.get(i.pk, [])
        except Exception as e:
            logger.debug(f"Error loading measurements for indicators: {e}")
            for i in indicators:
                indicator_measurements[i.pk] = []

    # Prepare inline mitigation update forms for the detailed page
    mitigation_form_pairs = []
    try:
        for m in mitigations:
            try:
                form = MitigationUpdateForm(instance=m)
            except Exception:
                form = None
            mitigation_form_pairs.append({'mitigation': m, 'form': form})
    except Exception:
        mitigation_form_pairs = []
    
    # Calculate risk priority based on score
    risk_score = risk.risk_rating if risk else 0
    if risk_score >= 20:
        risk_priority = {'level': 'Critical', 'class': 'danger'}
    elif risk_score >= 15:
        risk_priority = {'level': 'High', 'class': 'danger'}
    elif risk_score >= 8:
        risk_priority = {'level': 'Medium', 'class': 'warning'}
    else:
        risk_priority = {'level': 'Low', 'class': 'success'}
    
    # Determine status
    status = 'Draft' if (risk and risk.park_risk) else ('Approved' if (risk and risk.is_approved) else 'Pending Approval')
    
    # Mitigation statistics
    total_mitigations = mitigations.count()
    completed_mitigations = mitigations.filter(status='complete').count()
    in_progress_mitigations = mitigations.filter(status='in_progress').count()
    pending_mitigations = mitigations.filter(status='pending').count()
    
    # Calculate overdue mitigations
    from datetime import date
    overdue_mitigations = sum(1 for m in mitigations if m.is_overdue)
    
    mitigation_progress = (completed_mitigations / total_mitigations * 100) if total_mitigations > 0 else 0
    
    # Get assessments for this risk with their indicator assessments
    assessments = []
    all_assessments_with_indicators = []
    latest_assessment_data = None
    try:
        if risk and hasattr(risk, 'assessments'):
            assessments_attr = getattr(risk, 'assessments', None)
            if assessments_attr and hasattr(assessments_attr, 'all'):
                # Get basic assessments list for backward compatibility (all assessments, not just completed)
                assessments = assessments_attr.order_by('-assessment_date', '-created_at')
                logger.debug(f"DEBUG: Found {assessments.count()} total assessment records for risk {risk.risk_id}")
                
                # Get all assessments with their indicator assessments
                all_assessments_with_indicators = risk.get_all_assessments_with_indicators()
                logger.debug(f"DEBUG: Found {len(all_assessments_with_indicators)} assessments with indicators for risk {risk.risk_id}")
                
                # Get latest assessment with indicators
                latest_assessment_data = risk.latest_assessment_with_indicators
                if latest_assessment_data:
                    logger.debug(f"DEBUG: Latest assessment has {latest_assessment_data['total_indicators']} indicators")
                else:
                    logger.debug(f"DEBUG: No latest assessment data found for risk {risk.risk_id}")
    except (AttributeError, FieldError, Exception) as e:
        logger.exception("Error fetching assessments: %s", e)
        assessments = []
    
    # Get schedules for all indicators of this risk
    schedules = PeriodicMeasurementSchedule.objects.filter(
        indicator__risk=risk
    ).select_related('indicator', 'completed_measurement').order_by('scheduled_date')[:20]  # Next 20 schedules

    # Legacy support - keep for templates that still use these variables
    latest_assessment = None
    latest_assessment_indicators = None
    if latest_assessment_data:
        latest_assessment = latest_assessment_data['assessment']
        latest_assessment_indicators = {
            'total': latest_assessment_data['total_indicators'],
            'completed': latest_assessment_data['on_target'],
            'pending': latest_assessment_data['caution'] + latest_assessment_data['breached'],
        }

    # Note: Related risks section removed per request. Only display
    # the current risk's directly defined category impacts.
    
    context = {
        'risk': risk,
        'mitigations': mitigations,
        'controls': controls,
        'control_distribution': control_distribution,
        'residual_risk_data': residual_risk_data,
        'indicators': indicators,
        'indicator_measurements': indicator_measurements,
        'assessments': assessments,  # Basic assessments list
        'all_assessments_with_indicators': all_assessments_with_indicators,  # NEW: Assessments with indicators
        'latest_assessment_data': latest_assessment_data,  # NEW: Latest with full indicator data
        'schedules': schedules,
        'latest_assessment': latest_assessment,  # Legacy support
        'latest_assessment_indicators': latest_assessment_indicators,  # Legacy support
        'risk_priority': risk_priority,
        'risk_score': risk_score,
        'status': status,
        'total_mitigations': total_mitigations,
        'completed_mitigations': completed_mitigations,
        'in_progress_mitigations': in_progress_mitigations,
        'pending_mitigations': pending_mitigations,
        'overdue_mitigations': overdue_mitigations,
        'mitigation_progress': round(mitigation_progress, 1),
        'mitigation_form_pairs': mitigation_form_pairs,
        'page_title': f'Risk Details - {risk.risk_id if risk and hasattr(risk, "risk_id") else (risk.pk if risk else "Unknown")}'
    }
    logger.debug("Risk indicators: %s", indicators)  # debug

    return render(request, 'riskregister/detailed.html', context)

@login_required
def download_risk_report_pdf(request, risk_id):
    """Generate and download a corporate-styled comprehensive risk report as PDF."""

    # Parse formatted risk_id (e.g., R01SHO)
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if match:
        risk_number = int(match.group(1))
        dept_abbr = match.group(2)
        try:
            risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').get(
                risk_number=risk_number,
                department__abbreviation__iexact=dept_abbr
            )
        except Risk.DoesNotExist:
            return HttpResponse("Risk not found", status=404)
    else:
        return HttpResponse("Invalid risk ID format", status=404)

    mitigations = Mitigation.objects.filter(risk_id=risk.pk).select_related('responsible_person').order_by('due_date')
    indicators = RiskIndicator.objects.filter(risk_id=risk.pk).select_related('preferred_kpi').order_by('-created_at')

    # assessments may be a related name or an attribute - we try defensively
    assessments = []
    try:
        if hasattr(risk, 'assessments'):
            assessments_qs = getattr(risk, 'assessments')
            if assessments_qs is not None and hasattr(assessments_qs, 'all'):
                assessments = assessments_qs.all().order_by('-assessment_date', '-created_at')[:10]
    except (AttributeError, FieldError, Exception):
        assessments = []

    # --- Prepare PDF document ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=72,
        bottomMargin=72
    )

    # Corporate color palette and styles
    brand_primary = colors.HexColor("#0d47a1")   # deep corporate blue
    brand_accent = colors.HexColor("#1976d2")    # lighter blue
    neutral_gray = colors.HexColor("#6c757d")
    neutral_light = colors.HexColor("#f3f6fb")

    styles = getSampleStyleSheet()
    
    # Create custom styles with unique names or override existing ones
    styles['Title'].fontName = 'Helvetica-Bold'
    styles['Title'].fontSize = 26
    styles['Title'].alignment = TA_CENTER
    styles['Title'].textColor = brand_primary
    styles['Title'].spaceAfter = 12
    
    # Add custom styles that don't conflict
    if 'SubTitle' not in styles:
        styles.add(ParagraphStyle('SubTitle',
                                  parent=styles['Heading2'],
                                  fontName='Helvetica',
                                  fontSize=12,
                                  alignment=TA_CENTER,
                                  textColor=neutral_gray,
                                  spaceAfter=18))
    
    if 'SectionHeading' not in styles:
        styles.add(ParagraphStyle('SectionHeading',
                                  parent=styles['Heading2'],
                                  fontName='Helvetica-Bold',
                                  fontSize=14,
                                  textColor=brand_primary,
                                  spaceBefore=12,
                                  spaceAfter=6))
    
    if 'FieldLabel' not in styles:
        styles.add(ParagraphStyle('FieldLabel',
                                  parent=styles['Normal'],
                                  fontName='Helvetica-Bold',
                                  fontSize=10,
                                  textColor=neutral_gray,
                                  spaceAfter=2))
    
    if 'NormalCorporate' not in styles:
        styles.add(ParagraphStyle('NormalCorporate',
                                  parent=styles['Normal'],
                                  fontSize=10,
                                  textColor=colors.black,
                                  leading=13))
    
    if 'MutedSmall' not in styles:
        styles.add(ParagraphStyle('MutedSmall',
                                  parent=styles['Normal'],
                                  fontSize=9,
                                  textColor=neutral_gray))
    
    # Add style for table cell text wrapping
    if 'TableCell' not in styles:
        styles.add(ParagraphStyle('TableCell',
                                  parent=styles['Normal'],
                                  fontSize=9,
                                  textColor=colors.black,
                                  leading=11))

    # Store report metadata for footer
    report_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    generated_by = request.user.get_full_name() or request.user.username

    # Header / Footer functions
    def _header_footer(canvas, doc):
        canvas.saveState()
        # Header - a thin band with company name left and report title center
        canvas.setFillColor(brand_primary)
        canvas.rect(0, doc.height + doc.topMargin + 10, doc.width + doc.leftMargin + doc.rightMargin, 40, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(doc.leftMargin + 6, doc.height + doc.topMargin + 24, "RiskSuite")
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(doc.leftMargin + (doc.width / 2), doc.height + doc.topMargin + 24, "Comprehensive Risk Report")
        
        # Footer - with report date, generated by, and page number
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(neutral_gray)
        footer_left = f"Report Date: {report_date}"
        footer_center = f"Generated by: {generated_by}"
        page_num = f"Page {canvas.getPageNumber()}"
        
        canvas.drawString(doc.leftMargin, 30, footer_left)
        canvas.drawCentredString(doc.leftMargin + (doc.width / 2), 30, footer_center)
        canvas.drawRightString(doc.leftMargin + doc.width, 30, page_num)
        canvas.restoreState()

    elements = []

    # --- Cover page ---
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("RiskSuite", styles['Title']))
    elements.append(Paragraph("Comprehensive Risk Report", styles['SubTitle']))
    elements.append(Spacer(1, 0.3 * inch))

    # --- Risk rating badge / quick metrics ---
    try:
        current_score = assessments[0].risk_score if assessments else (risk.risk_rating or 0)
    except Exception:
        current_score = risk.risk_rating or 0

    if current_score >= 20:
        risk_level = "CRITICAL"
        risk_color = colors.HexColor("#b00020")
    elif current_score >= 15:
        risk_level = "HIGH"
        risk_color = colors.HexColor("#ff9800")
    elif current_score >= 8:
        risk_level = "MEDIUM"
        risk_color = colors.HexColor("#ffd54f")
    else:
        risk_level = "LOW"
        risk_color = colors.HexColor("#2e7d32")

    rating_table = Table([
        ['Risk Rating', str(current_score) + "/25", 'Level', risk_level]
    ], colWidths=[1.4*inch, 1.1*inch, 0.9*inch, 1.8*inch])
    rating_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (3, 0), (3, 0), 'CENTER'),
        ('BACKGROUND', (3, 0), (3, 0), risk_color),
        ('TEXTCOLOR', (3, 0), (3, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e3eefb')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(rating_table)
    elements.append(Spacer(1, 0.25 * inch))

    # --- Risk Details Section ---
    elements.append(Paragraph("Risk Details", styles['SectionHeading']))

    details_data = [
        ['Title', risk.title or '—'],
        ['Risk ID', getattr(risk, 'risk_id', '—')],
        ['Department', risk.department.name if getattr(risk, 'department', None) else '—'],
        ['Category', risk.category.name if getattr(risk, 'category', None) else '—'],
        ['Risk Owner', getattr(risk.risk_owner, 'name', str(risk.risk_owner)) if getattr(risk, 'risk_owner', None) else '—'],
        ['Parked (Draft)', 'Yes' if getattr(risk, 'park_risk', False) else 'No'],
        ['Approved', 'Yes' if getattr(risk, 'is_approved', False) else 'No'],
    ]
    details_table = Table(details_data, colWidths=[1.6*inch, 4.9*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fbff')),
        ('TEXTCOLOR', (0, 0), (0, -1), neutral_gray),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#eef4ff')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Description / Cause / Impact
    elements.append(Paragraph("Description", styles['SectionHeading']))
    elements.append(Paragraph(risk.description or "No description provided.", styles['NormalCorporate']))
    elements.append(Spacer(1, 0.08 * inch))

    elements.append(Paragraph("Root Cause", styles['SectionHeading']))
    elements.append(Paragraph(risk.cause or "No cause recorded.", styles['NormalCorporate']))
    elements.append(Spacer(1, 0.08 * inch))

    elements.append(Paragraph("Business Impact", styles['SectionHeading']))
    elements.append(Paragraph(risk.impact_description or "No business impact described.", styles['NormalCorporate']))
    elements.append(Spacer(1, 0.2 * inch))

    # --- Assessments (if any) ---
    if assessments:
        elements.append(Paragraph("Assessment History", styles['SectionHeading']))
        assessment_data = [['Date', 'Type', 'Likelihood', 'Impact', 'Score', 'Level']]
        for a in assessments[:8]:
            try:
                a_date = getattr(a, 'assessment_date', None)
                date_str = a_date.strftime("%b %d, %Y") if a_date else '—'
            except Exception:
                date_str = '—'
            likelihood = f"{getattr(a, 'likelihood', '-')}/5"
            impact_val = f"{getattr(a, 'impact', '-')}/5"
            score = getattr(a, 'risk_score', '-')
            try:
                sc = int(score)
            except Exception:
                sc = None
            if sc is not None:
                if sc >= 20:
                    level = "CRITICAL"
                elif sc >= 15:
                    level = "HIGH"
                elif sc >= 8:
                    level = "MEDIUM"
                else:
                    level = "LOW"
            else:
                level = "—"
            assessment_data.append([date_str, getattr(a, 'get_assessment_type_display', lambda: '-')(), likelihood, impact_val, str(score), level])

        table = Table(assessment_data, colWidths=[1.1*inch, 1.4*inch, 1*inch, 1*inch, 0.8*inch, 1.0*inch])
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), brand_primary),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e7eefc')),
        ])
        for i in range(1, len(assessment_data)):
            if i % 2 == 0:
                tbl_style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
        table.setStyle(tbl_style)
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))

    # --- Indicators ---
    if indicators:
        elements.append(Paragraph("Risk Indicators", styles['SectionHeading']))
        for indicator in indicators:
            # Get indicator name - prefer KPI name, fallback to custom name, then default
            if indicator.preferred_kpi:
                name = indicator.preferred_kpi.name
            elif indicator.preferred_kpi_name:
                name = indicator.preferred_kpi_name
            else:
                name = "Unnamed Indicator"
            
            elements.append(Paragraph(name, ParagraphStyle('indTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=brand_accent)))
            ind_rows = [
                ['Appetite Level:', str(getattr(indicator, 'appetite_level', '—')).title()],
                ['Tolerance (%):', f"{getattr(indicator, 'appetite_tolerance_pct', '—')}%"],
                ['Aggregation:', str(getattr(indicator, 'aggregation_method', '—')).title()],
                ['Measurement Period:', str(getattr(indicator, 'measurement_period', '—')).replace('_', ' ').title()]
            ]
            ind_table = Table(ind_rows, colWidths=[1.6*inch, 4.9*inch])
            ind_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fbfcff')),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#eef4ff')),
            ]))
            elements.append(ind_table)
            if getattr(indicator, 'notes', None):
                elements.append(Paragraph("Notes", styles['MutedSmall']))
                elements.append(Paragraph(indicator.notes, styles['NormalCorporate']))
            elements.append(Spacer(1, 0.12*inch))

    # --- Mitigations ---
    if mitigations:
        elements.append(Paragraph("Mitigation Actions & Status", styles['SectionHeading']))
        mitigation_data = [[Paragraph('Action', styles['TableCell']), Paragraph('Status', styles['TableCell']), Paragraph('Responsible', styles['TableCell']), Paragraph('Due Date', styles['TableCell'])]]
        for m in mitigations:
            action_text = getattr(m, 'action', getattr(m, 'description', '—'))
            status = getattr(m, 'status', '—')
            # Format status string (replace underscores with spaces and title case)
            status = str(status).replace('_', ' ').title() if status != '—' else '—'
            responsible = str(getattr(m, 'responsible_person', 'Unassigned'))
            due_date = getattr(m, 'due_date', None)
            due_str = due_date.strftime("%b %d, %Y") if due_date else 'Not set'
            
            # Wrap all cells in Paragraph for consistent text wrapping
            action_para = Paragraph(action_text, styles['TableCell'])
            status_para = Paragraph(status, styles['TableCell'])
            responsible_para = Paragraph(responsible, styles['TableCell'])
            due_para = Paragraph(due_str, styles['TableCell'])
            mitigation_data.append([action_para, status_para, responsible_para, due_para])

        mit_table = Table(mitigation_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1*inch])
        mit_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), brand_primary),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e7eefc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
        for i in range(1, len(mitigation_data)):
            if i % 2 == 0:
                mit_style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
        mit_table.setStyle(mit_style)
        elements.append(mit_table)
        elements.append(Spacer(1, 0.2*inch))

    # --- Final notes & footer ---
    elements.append(Paragraph("Notes & Recommendations", styles['SectionHeading']))
    elements.append(Paragraph("This report is system-generated and intended for management review. For detailed audit trails, check the risk history and mitigation logs in RiskSuite.", styles['MutedSmall']))
    elements.append(Spacer(1, 0.3 * inch))

    # Build PDF with header/footer on each page
    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    filename = f"Risk_Report_{getattr(risk, 'risk_id', risk.pk)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response

@login_required
def edit_risk(request, risk_id):
    """
    Multi-stage risk editing workflow:
    Stage 1: Basic risk information
    Stage 2: Inherent risk assessment and internal controls
    Stage 3: View residual risk rating
    """
    stage = request.GET.get('stage', '1')
    
    # Get the risk object by risk_id (e.g., "R01FN", "R03OP") or by pk if numeric
    try:
        # If it's purely numeric, treat as pk
        if risk_id.isdigit():
            risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').get(pk=int(risk_id))
        else:
            # Parse risk_id format: R{number}{dept_abbr} e.g., "R03OP", "R01FN"
            import re
            match = re.match(r'R(\d+)([A-Z]+)', risk_id.upper())
            if match:
                number = int(match.group(1))
                dept_abbr = match.group(2)
                # Query by risk_number and department abbreviation
                risk = Risk.objects.select_related('department', 'category', 'risk_owner', 'linked_kpi').get(
                    risk_number=number,
                    department__abbreviation__iexact=dept_abbr
                )
            else:
                return HttpResponse("Invalid risk ID format", status=404)
    except Risk.DoesNotExist:
        return HttpResponse("Risk not found", status=404)
    
    # Get existing indicators for this risk
    existing_indicators = RiskIndicator.objects.filter(risk_id=risk.pk).order_by('created_at')
    
    # Stage 1: Basic Information
    if stage == '1':
        if request.method == 'POST':
            risk_form = RiskBasicInfoForm(request.POST, instance=risk)
            category_formset = RiskCategoryImpactFormSet(request.POST, instance=risk)
            
            if risk_form.is_valid() and category_formset.is_valid():
                # Update the risk - use commit=False to handle risk_number properly
                updated_risk = risk_form.save(commit=False)
                
                # Check if department has changed
                if updated_risk.department != risk.department:
                    # Department changed - need to assign new risk_number for the new department
                    last_risk = Risk.all_objects.filter(department=updated_risk.department).order_by('-risk_number').first()
                    updated_risk.risk_number = 1 if not last_risk or not last_risk.risk_number else last_risk.risk_number + 1
                    logger.debug(f"Department changed from {risk.department} to {updated_risk.department}, assigned new risk_number: {updated_risk.risk_number}")
                else:
                    # Department unchanged - preserve existing risk_number
                    updated_risk.risk_number = risk.risk_number
                
                updated_risk.save()
                
                # Save category impacts updates
                try:
                    category_formset.save()
                except Exception as e:
                    logger.exception("Error saving category impacts: %s", e)
                
                messages.success(request, f'Risk "{risk.title}" basic information updated! Now review inherent risk assessment and controls.')
                
                # Redirect to stage 2
                return redirect(f"{request.path}?stage=2")
            else:
                logger.debug("Risk form errors: %s", risk_form.errors)
                try:
                    logger.debug("Category formset errors: %s", category_formset.errors)
                except Exception:
                    pass
        else:
            risk_form = RiskBasicInfoForm(instance=risk)
            category_formset = RiskCategoryImpactFormSet(instance=risk)
        
        kpis = KPI.objects.all().order_by('name')
        
        return render(request, 'risk_form_stage1.html', {
            'risk_form': risk_form,
            'category_formset': category_formset,
            'kpis': kpis,
            'stage': 1,
            'total_stages': 4,
            'is_edit': True,
            'risk': risk,
        })
    
    # Stage 2: Inherent Assessment and Controls
    elif stage == '2':
        if request.method == 'POST':
            assessment_form = RiskInherentAssessmentForm(request.POST, instance=risk)
            control_formset = ControlFormSet(request.POST, instance=risk, prefix='controls')
            
            if assessment_form.is_valid() and control_formset.is_valid():
                # Save inherent assessment
                updated_risk = assessment_form.save(commit=False)
                updated_risk.save()
                
                # Save controls
                try:
                    controls = control_formset.save(commit=False)
                    for control in controls:
                        control.risk = updated_risk
                        if not control.created_by:
                            control.created_by = request.user
                        control.save()
                    control_formset.save_m2m()
                    
                    # Handle deleted controls
                    for deleted_control in control_formset.deleted_objects:
                        deleted_control.delete()
                except Exception as e:
                    logger.exception("Error saving controls: %s", e)
                
                messages.success(request, f'Inherent assessment and controls updated! Review residual risk rating.')
                
                # Redirect to stage 3 (residual risk view)
                return redirect(f"{request.path}?stage=3")
            else:
                logger.debug("Assessment form errors: %s", assessment_form.errors)
                logger.debug("Control formset errors: %s", control_formset.errors)
        else:
            assessment_form = RiskInherentAssessmentForm(instance=risk)
            control_formset = ControlFormSet(instance=risk, prefix='controls')
        
        return render(request, 'risk_form_stage2.html', {
            'risk': risk,
            'assessment_form': assessment_form,
            'control_formset': control_formset,
            'stage': 2,
            'total_stages': 4,
            'is_edit': True,
            'existing_indicators': existing_indicators,
        })
    
    # Stage 3: Residual Risk Rating
    elif stage == '3':
        if request.method == 'POST':
            # Handle status based on action button clicked
            action = request.POST.get('action', 'park')
            if action == 'submit':
                risk.status = 'pending'
                risk.park_risk = False
            else:  # park or default
                risk.status = 'parked'
                risk.park_risk = True
            
            risk.save()
            
            # Clear draft session
            if 'draft_risk_id' in request.session:
                del request.session['draft_risk_id']
            
            # Store risk ID for indicator workflow
            request.session['new_risk_id'] = risk.pk
            request.session['workflow_step'] = 'add_indicators'
            
            messages.success(request, f'Risk "{risk.title}" created successfully! Now add risk indicators.')
            
            # Redirect to add indicators page
            return redirect('add_indicator', risk_id=risk.pk)
        
        # Calculate residual risk
        residual_data = risk.calculate_residual_risk()
        controls = risk.controls.filter(is_active=True).order_by('-weight', 'control_type')
        
        return render(request, 'risk_form_stage3.html', {
            'risk': risk,
            'residual_data': residual_data,
            'controls': controls,
            'stage': 3,
            'total_stages': 4,
            'is_edit': True,
            'existing_indicators': existing_indicators,
        })
    
    else:
        messages.error(request, 'Invalid stage.')
        return redirect('edit_risk', risk_id=risk_id)


@login_required
def add_assessment(request, risk_id):
    """
    Risk assessments are now automatically generated from indicator assessments.
    This view redirects users to assess indicators or shows the latest auto-generated assessment.
    """
    logger.debug(f"DEBUG: add_assessment called with risk_id={risk_id}")
    
    # Resolve risk by formatted `risk_id` (e.g. R01OP -> risk_number + department)
    # or fall back to numeric PK for legacy links.
    rid = str(risk_id)
    m = re.match(r"R?(?P<num>\d+)(?P<dept>[A-Za-z]+)$", rid)
    risk = None
    if m:
        num = int(m.group('num'))
        dept_abbr = m.group('dept')
        try:
            risk = Risk.objects.get(risk_number=num, department__abbreviation__iexact=dept_abbr)
            logger.debug(f"DEBUG: Resolved risk by risk_number+dept: {risk.pk} (R{num}{dept_abbr})")
        except Risk.DoesNotExist:
            risk = None

    if risk is None:
        # Fallback: extract first numeric substring and treat as PK
        numbers = re.findall(r'\d+', rid)
        if not numbers:
            messages.error(request, 'Invalid risk ID format')
            return redirect('all_risks')
        numeric_id = int(numbers[0])
        logger.debug(f"DEBUG: Parsed numeric_id={numeric_id} (fallback to PK)")
        try:
            risk = Risk.objects.get(pk=numeric_id)
        except Risk.DoesNotExist:
            messages.error(request, 'Risk not found')
            return redirect('all_risks')
    
    # Safety check - ensure risk has been saved with a primary key
    if not risk or not risk.pk:
        messages.error(request, 'Risk object is not valid')
        return redirect('all_risks')
    
    # Check if risk has indicators
    indicators = RiskIndicator.objects.filter(risk_id=risk.pk, active=True)
    logger.debug(f"DEBUG: Found {indicators.count()} active indicators")
    
    if not indicators.exists():
        messages.warning(
            request,
            'Please add Key Risk Indicators first. Risk assessments are automatically generated after assessing indicators.'
        )
        logger.debug(f"DEBUG: No indicators, redirecting to add_indicator")
        return redirect('add_indicator', risk_id=risk.pk)
    
    # Check if all indicators have been assessed
    assessed_indicators = IndicatorAssessment.objects.filter(
        indicator__risk_id=risk.pk,
        is_current=True
    ).values_list('indicator_id', flat=True)
    
    unassessed_indicators = indicators.exclude(id__in=assessed_indicators)
    logger.debug(f"DEBUG: {unassessed_indicators.count()} unassessed indicators out of {indicators.count()}")

    # Allow forcing a new assessment workflow even if indicators already have current assessments
    force_start = str(request.GET.get('force', '')).lower() in ('1', 'true', 'yes')
    if force_start:
        logger.debug("DEBUG: force flag detected - starting assessment workflow")
        first_to_assess = indicators.order_by('created_at').first()
        if first_to_assess:
            return redirect('record_indicator_assessment_for_indicator', indicator_id=first_to_assess.pk)

    if unassessed_indicators.exists():
        messages.info(
            request,
            f'Please assess all {indicators.count()} indicators. {unassessed_indicators.count()} indicator(s) still need assessment. '
            'The overall risk assessment will be automatically generated.'
        )
        # Redirect to first unassessed indicator
        first_unassessed = unassessed_indicators.order_by('created_at').first()
        if first_unassessed:
            logger.debug(f"DEBUG: Redirecting to assess indicator {first_unassessed.pk}")
            return redirect('record_indicator_assessment_for_indicator', indicator_id=first_unassessed.pk)
        # fallback
        first_unassessed = unassessed_indicators.first()
        if first_unassessed:
            logger.debug(f"DEBUG: Redirecting to assess indicator {first_unassessed.pk}")
            return redirect('record_indicator_assessment_for_indicator', indicator_id=first_unassessed.pk)
    
    # All indicators assessed - present manual assessment form showing indicator results
    # Show the manual assessment form when:
    # 1. User explicitly requested show_indicator_results query param
    # 2. User completed all indicators and was redirected here
    # 3. POST request (user submitting the assessment)
    show_indicator_results = str(request.GET.get('show_indicator_results', '')).lower() in ('1', 'true', 'yes')

    if request.method == 'POST' or show_indicator_results or (not unassessed_indicators.exists() and indicators.exists()):
        if request.method == 'POST':
            form = ManualRiskAssessmentForm(request.POST)
            if form.is_valid():
                # mark previous as not current
                RiskAssessment.objects.filter(risk_id=risk.pk).update(is_current=False)

                assessment = form.save(commit=False)
                assessment.risk = risk
                assessment.assessor = request.user if request.user.is_authenticated else None
                # If this is the very first assessment for the risk, record it as 'initial'
                has_existing = RiskAssessment.objects.filter(risk_id=risk.pk).exists()
                if not has_existing:
                    assessment.assessment_type = 'initial'
                else:
                    # preserve form value or default to periodic
                    assessment.assessment_type = assessment.assessment_type or 'periodic'

                assessment.status = 'completed'
                assessment.is_current = True
                assessment.save()

                # link current indicator assessments
                indicator_assessments = IndicatorAssessment.objects.filter(indicator__risk_id=risk.pk, is_current=True)
                assessment.source_indicator_assessments.set(indicator_assessments)

                # update risk likelihood/impact from manual values
                risk.likelihood = assessment.likelihood
                risk.impact = assessment.impact
                risk.save(update_fields=['likelihood', 'impact'])

                messages.success(request, 'Risk assessment saved manually.')
                return redirect('risk_detail', risk_id=risk.risk_id)
        else:
            # If there are no existing assessments for this risk, default to 'initial'
            default_type = 'initial' if not RiskAssessment.objects.filter(risk_id=risk.pk).exists() else 'periodic'
            form = ManualRiskAssessmentForm(initial={
                'assessment_date': date.today(),
                'assessment_type': default_type,
            })

        # prepare indicator assessment summary for the template
        indicator_assessments = IndicatorAssessment.objects.filter(indicator__risk_id=risk.pk, is_current=True).select_related('indicator')
        indicators_summary = []
        for ia in indicator_assessments:
            indicators_summary.append({
                'indicator': ia.indicator,
                'status': ia.status,
                'measured_value': ia.measured_value,
                'assessment_date': ia.assessment_date,
                'rationale': ia.analysis or ia.assessment_notes,
            })

        # Get assessment history
        all_assessments_with_indicators = []
        try:
            all_assessments_with_indicators = risk.get_all_assessments_with_indicators()
            logger.debug(f"DEBUG: Found {len(all_assessments_with_indicators)} assessments with indicators for risk {risk.risk_id}")
        except Exception as e:
            logger.exception("ERROR getting assessment history: %s", e)

        context = {
            'risk': risk,
            'form': form,
            'indicators_summary': indicators_summary,
            'all_assessments_with_indicators': all_assessments_with_indicators,
            'form_title': 'Manual Risk Assessment (based on indicator results)'
        }

        return render(request, 'riskregister/manual_assessment_form.html', context)

    # Redirect back to risk detail page by default
    return redirect('risk_detail', risk_id=risk.risk_id)


@login_required
def add_mitigation(request, risk_id):
    """Add a new mitigation action for a risk"""
    # Parse formatted risk_id (e.g., R01SHO)
    match = re.match(r'^R?(\d+)([A-Z]{2,})$', str(risk_id).upper())
    if match:
        risk_number = int(match.group(1))
        dept_abbr = match.group(2)
        try:
            risk = Risk.objects.get(
                risk_number=risk_number,
                department__abbreviation__iexact=dept_abbr
            )
        except Risk.DoesNotExist:
            return HttpResponse("Risk not found", status=404)
    else:
        return HttpResponse("Invalid risk ID format", status=404)
    
    if request.method == 'POST':
        form = MitigationForm(request.POST, request.FILES)
        if form.is_valid():
            mitigation = form.save(commit=False)
            mitigation.risk = risk
            mitigation.save()
            
            return redirect('risk_detail', risk_id=risk.risk_id)
        else:
            logger.debug("Mitigation form errors: %s", form.errors)
    else:
        form = MitigationForm()
    
    context = {
        'form': form,
        'risk': risk,
        'form_title': 'Add Mitigation Action',
        'form_type': 'mitigation',
    }
    
    return render(request, 'riskregister/mitigation_form.html', context)


@login_required
def update_mitigation(request, mitigation_id):
    """Update mitigation status and optionally trigger risk reassessment"""
    mitigation = get_object_or_404(Mitigation, pk=mitigation_id)
    risk = mitigation.risk
    old_status = mitigation.status
    old_completion = mitigation.completion_percentage
    old_due_date = mitigation.due_date
    
    if request.method == 'POST':
        form = MitigationUpdateForm(request.POST, request.FILES, instance=mitigation)
        if form.is_valid():
            progress_notes = form.cleaned_data.get('progress_notes', '')
            postponement_reason = form.cleaned_data.get('postponement_reason', '')
            failure_reason = form.cleaned_data.get('failure_reason', '')
            lessons_learned = form.cleaned_data.get('lessons_learned', '')
            trigger_reassessment = form.cleaned_data.get('trigger_reassessment', False)
            
            # Save the mitigation with updated status
            updated_mitigation = form.save(commit=False)
            new_status = updated_mitigation.status
            new_completion = updated_mitigation.completion_percentage
            new_due_date = updated_mitigation.due_date
            
            # Track if this is the first time setting original_due_date
            if not updated_mitigation.original_due_date and new_due_date:
                updated_mitigation.original_due_date = new_due_date
            
            # Handle postponement
            if new_status == 'postponed':
                updated_mitigation.postponement_count += 1
                updated_mitigation.last_postponed_date = timezone.now().date()
            
            updated_mitigation.save()
            
            # Determine action type for progress log
            action_type = 'status_change'
            if new_status == 'postponed':
                action_type = 'postponed'
            elif new_status == 'not_achieved':
                action_type = 'completion_failed'
            elif new_status == 'partially_implemented':
                action_type = 'partial_completion'
            elif new_status == 'cancelled':
                action_type = 'cancelled'
            elif old_completion != new_completion:
                action_type = 'progress_update'
            elif old_due_date != new_due_date:
                action_type = 'due_date_extended'
            
            # Create detailed progress log
            progress_log = mitigation.record_progress_update(
                user=request.user if request.user.is_authenticated else None,
                action_type=action_type,
                notes=progress_notes,
                previous_status=old_status,
                previous_completion_percentage=old_completion,
                previous_due_date=old_due_date,
                completion_percentage=new_completion,
                due_date_at_time=new_due_date,
                postponement_reason=postponement_reason,
                new_target_date=new_due_date if new_status == 'postponed' else None,
                failure_reason=failure_reason,
                lessons_learned=lessons_learned,
                evidence=form.cleaned_data.get('evidence') if form.cleaned_data.get('evidence') else None,
            )
            
            # Log to ActivityLog for backward compatibility
            ActivityLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action='mitigation_updated',
                object_type='Mitigation',
                object_id=str(mitigation.pk),
                description=f'Mitigation status updated from {old_status} to {new_status}',
                context={
                    'mitigation_id': mitigation.pk,
                    'risk_id': risk.pk,
                    'risk_number': risk.risk_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'old_completion': old_completion,
                    'new_completion': new_completion,
                    'progress_notes': progress_notes,
                    'postponement_reason': postponement_reason,
                    'failure_reason': failure_reason,
                    'trigger_reassessment': trigger_reassessment,
                }
            )
            
            # Handle specific status changes
            if new_status == 'complete' and old_status != 'complete':
                ActivityLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='mitigation_completed',
                    object_type='Mitigation',
                    object_id=str(mitigation.pk),
                    description=f'Mitigation action completed for risk {risk.risk_id}',
                    context={
                        'mitigation_id': mitigation.pk,
                        'risk_id': risk.pk,
                        'risk_number': risk.risk_id,
                        'action': mitigation.action,
                        'strategy': mitigation.strategy,
                    }
                )
                messages.success(request, f'Mitigation marked as complete!')
            elif new_status == 'postponed':
                messages.warning(request, f'Mitigation postponed. Total postponements: {mitigation.postponement_count}')
            elif new_status == 'not_achieved':
                messages.error(request, 'Mitigation marked as not achieved. Please review and plan next steps.')
            elif new_status == 'partially_implemented':
                messages.info(request, f'Mitigation partially implemented at {new_completion}%')
            else:
                messages.success(request, f'Mitigation status updated to {new_status}')
            
            # If reassessment is triggered or mitigation completed, redirect to reassessment
            if trigger_reassessment or (new_status == 'complete' and old_status != 'complete'):
                # Log that reassessment is being triggered
                ActivityLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='reassessment_triggered',
                    object_type='Risk',
                    object_id=str(risk.pk),
                    description=f'Risk reassessment triggered by mitigation update',
                    context={
                        'risk_id': risk.pk,
                        'risk_number': risk.risk_id,
                        'mitigation_id': mitigation.pk,
                        'trigger_reason': 'mitigation_completed' if new_status == 'complete' else 'manual_trigger',
                    }
                )
                messages.info(request, 'Please reassess the risk based on the mitigation progress.')
                return redirect('add_assessment', risk_id=risk.pk)
            
            return redirect('risk_detail', risk_id=risk.risk_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MitigationUpdateForm(instance=mitigation)
    
    # Get progress history
    progress_history = MitigationProgressLog.objects.filter(
        mitigation=mitigation
    ).select_related('user').order_by('-created_at')[:20]
    
    context = {
        'form': form,
        'mitigation': mitigation,
        'risk': risk,
        'form_title': 'Update Mitigation Status',
        'old_status': old_status,
        'progress_history': progress_history,
    }
    
    return render(request, 'riskregister/mitigation_update_form.html', context)


@login_required
def mitigation_progress_trail(request, mitigation_id):
    """Display detailed progression trail for a mitigation"""
    mitigation = get_object_or_404(Mitigation, pk=mitigation_id)
    risk = mitigation.risk
    
    # Get all progress logs
    progress_logs = MitigationProgressLog.objects.filter(
        mitigation=mitigation
    ).select_related('user').order_by('-created_at')
    
    # Calculate statistics
    total_updates = progress_logs.count()
    status_changes = progress_logs.filter(action_type='status_change').count()
    postponements = mitigation.postponement_count
    
    # Calculate average time between updates
    if total_updates > 1:
        first_log = progress_logs.last()
        latest_log = progress_logs.first()
        if first_log and latest_log and first_log.created_at and latest_log.created_at:
            days_span = (latest_log.created_at - first_log.created_at).days
            avg_days_between_updates = days_span / (total_updates - 1) if total_updates > 1 else 0
        else:
            avg_days_between_updates = 0
    else:
        avg_days_between_updates = 0
    
    context = {
        'mitigation': mitigation,
        'risk': risk,
        'progress_logs': progress_logs,
        'total_updates': total_updates,
        'status_changes': status_changes,
        'postponements': postponements,
        'avg_days_between_updates': round(avg_days_between_updates, 1),
        'page_title': f'Mitigation Progress Trail - {mitigation.action[:50]}',
    }
    
    return render(request, 'riskregister/mitigation_progress_trail.html', context)


@login_required
def update_schedule(request, schedule_id):
    """Update a periodic measurement schedule and optionally record a measurement"""
    schedule = get_object_or_404(PeriodicMeasurementSchedule, pk=schedule_id)
    risk = schedule.indicator.risk
    
    if request.method == 'POST':
        form = ScheduleUpdateForm(request.POST, instance=schedule)
        if form.is_valid():
            # Save the schedule
            updated_schedule = form.save(commit=False)
            
            # If status is completed and measurement value provided, create measurement
            if updated_schedule.status == 'completed' and form.cleaned_data.get('measurement_value'):
                measurement = IndicatorMeasurement.objects.create(
                    indicator=schedule.indicator,
                    measured_at=timezone.now(),
                    value=form.cleaned_data['measurement_value'],
                    notes=form.cleaned_data.get('measurement_notes', '')
                )
                
                # Link the measurement to the schedule
                updated_schedule.mark_completed(measurement, user=request.user if request.user.is_authenticated else None)
            else:
                updated_schedule.save()
            
            return redirect('risk_detail', risk_id=risk.risk_id)
        else:
            logger.debug("Schedule update form errors: %s", form.errors)
    else:
        form = ScheduleUpdateForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'risk': risk,
        'indicator': schedule.indicator,
        'form_title': 'Update Measurement Schedule',
    }
    
    return render(request, 'riskregister/schedule_form.html', context)


@login_required
def record_indicator_assessment(request, schedule_id):
    """Record a comprehensive indicator assessment from a schedule"""
    schedule = get_object_or_404(PeriodicMeasurementSchedule, pk=schedule_id)
    indicator = schedule.indicator
    risk = indicator.risk
    
    if request.method == 'POST':
        form = IndicatorAssessmentForm(
            request.POST, 
            request.FILES,
            indicator=indicator,
            schedule=schedule
        )
        if form.is_valid():
            # Use the class method to create assessment from schedule
            assessment = IndicatorAssessment.create_from_schedule(
                schedule=schedule,
                measured_value=form.cleaned_data['measured_value'],
                notes=form.cleaned_data.get('assessment_notes', ''),
                assessed_by=request.user if request.user.is_authenticated else None
            )
            
            # Update additional fields from form
            assessment.is_financial = form.cleaned_data.get('is_financial', False)
            assessment.currency_code = form.cleaned_data.get('currency_code', 'USD')
            assessment.analysis = form.cleaned_data.get('analysis', '')
            assessment.corrective_actions = form.cleaned_data.get('corrective_actions', '')
            
            if form.cleaned_data.get('evidence_documents'):
                assessment.evidence_documents = form.cleaned_data['evidence_documents']
            
            assessment.save()
            
            messages.success(request, 'Indicator assessment recorded successfully!', extra_tags='assessment_saved')
            
            # Check if there are remaining unassessed indicators for the same risk
            all_indicators = RiskIndicator.objects.filter(risk_id=risk.pk, active=True)
            assessed_indicator_ids = IndicatorAssessment.objects.filter(
                indicator__risk_id=risk.pk,
                is_current=True
            ).values_list('indicator_id', flat=True)
            unassessed = all_indicators.exclude(id__in=assessed_indicator_ids)

            if unassessed.exists():
                # More indicators to assess - continue to next unassessed indicator
                next_indicator = unassessed.order_by('created_at').first()
                if next_indicator:
                    messages.info(request, f'{unassessed.count()} more indicator(s) need assessment.')
                    return redirect('record_indicator_assessment_for_indicator', indicator_id=next_indicator.pk)
            else:
                # All indicators assessed - check if there are controls to assess
                active_controls = Control.objects.filter(risk_id=risk.pk, is_active=True)
                if active_controls.exists():
                    messages.success(request, 'All indicators assessed! Now assess control effectiveness.')
                    return redirect('assess_controls', risk_id=risk.risk_id)
                else:
                    # No controls - proceed to risk assessment
                    messages.success(request, 'All indicators assessed! Please complete the overall risk assessment.')
                    return redirect(f'/risks/{risk.risk_id}/add-assessment/?show_indicator_results=1')
        else:
            logger.debug("Indicator assessment form errors: %s", form.errors)
    else:
        form = IndicatorAssessmentForm(indicator=indicator, schedule=schedule)
    
    # Get workflow context
    is_workflow = (request.session.get('workflow_step') == 'assess_indicators' and 
                   request.session.get('new_risk_id') == risk.pk)
    indicators_count = RiskIndicator.objects.filter(risk_id=risk.pk).count()
    assessed_count = IndicatorAssessment.objects.filter(indicator__risk_id=risk.pk).values('indicator').distinct().count()

    context = {
        'form': form,
        'indicator': indicator,
        'risk': risk,
        'schedule': schedule,
        'form_title': 'Record Indicator Assessment',
        'is_workflow': is_workflow,
        'indicators_count': indicators_count,
        'assessed_count': assessed_count,
    }

    return render(request, 'riskregister/indicator_assessment_form.html', context)


@login_required
def record_indicator_assessment_for_indicator(request, indicator_id):
    """Record an indicator assessment directly for an indicator (no schedule)."""
    indicator = get_object_or_404(RiskIndicator, pk=indicator_id)
    risk = indicator.risk
    
    # Check if this is part of the new risk workflow
    is_workflow = (request.session.get('workflow_step') == 'assess_indicators' and 
                   request.session.get('new_risk_id') == risk.pk)

    if request.method == 'POST':
        form = IndicatorAssessmentForm(request.POST, request.FILES, indicator=indicator, schedule=None)
        if form.is_valid():
            measured_value = form.cleaned_data['measured_value']
            notes = form.cleaned_data.get('assessment_notes', '')

            # Create measurement record
            measurement = IndicatorMeasurement.objects.create(
                indicator=indicator,
                measured_at=timezone.now(),
                value=measured_value,
                notes=notes,
            )

            # Get previous assessment and mark others as not current
            previous = IndicatorAssessment.objects.filter(indicator=indicator, is_current=True).first()
            IndicatorAssessment.objects.filter(indicator=indicator).update(is_current=False)

            # Use form values for financial/currency
            is_financial = form.cleaned_data.get('is_financial', False)
            currency_code = form.cleaned_data.get('currency_code', 'USD')

            assessment_date = form.cleaned_data.get('assessment_date') or date.today()

            # Check if assessment already exists for this date
            existing_assessment = IndicatorAssessment.objects.filter(
                indicator=indicator,
                assessment_date=assessment_date
            ).first()
            
            if existing_assessment:
                # Update existing assessment
                existing_assessment.measurement = measurement
                existing_assessment.measured_value = measured_value
                existing_assessment.previous_value = previous.measured_value if previous else None
                existing_assessment.is_financial = is_financial
                existing_assessment.currency_code = currency_code
                existing_assessment.assessment_notes = form.cleaned_data.get('assessment_notes', '')
                existing_assessment.analysis = form.cleaned_data.get('analysis', '')
                existing_assessment.corrective_actions = form.cleaned_data.get('corrective_actions', '')
                evidence_doc = form.cleaned_data.get('evidence_documents')
                if evidence_doc:
                    existing_assessment.evidence_documents = evidence_doc
                existing_assessment.assessed_by = request.user if request.user.is_authenticated else None
                existing_assessment.is_current = True
                existing_assessment.save()
                assessment = existing_assessment
            else:
                # Create new assessment
                assessment = IndicatorAssessment.objects.create(
                    indicator=indicator,
                    schedule=None,
                    measurement=measurement,
                    assessment_date=assessment_date,
                    assessment_period_start=assessment_date,
                    assessment_period_end=assessment_date,
                    measured_value=measured_value,
                    previous_value=previous.measured_value if previous else None,
                    is_financial=is_financial,
                    currency_code=currency_code,
                    assessment_notes=form.cleaned_data.get('assessment_notes', ''),
                    analysis=form.cleaned_data.get('analysis', ''),
                    corrective_actions=form.cleaned_data.get('corrective_actions', ''),
                    evidence_documents=form.cleaned_data.get('evidence_documents') if form.cleaned_data.get('evidence_documents') else None,
                    assessed_by=request.user if request.user.is_authenticated else None,
                    is_current=True,
                )

            # Tag this message so UI displays a single popup toast confirmation
            messages.success(request, 'Indicator assessment recorded successfully!', extra_tags='assessment_saved')
            
            # Check if there are remaining unassessed indicators
            all_indicators = RiskIndicator.objects.filter(risk_id=risk.pk, active=True)
            assessed_indicator_ids = IndicatorAssessment.objects.filter(
                indicator__risk_id=risk.pk,
                is_current=True
            ).values_list('indicator_id', flat=True)
            unassessed = all_indicators.exclude(id__in=assessed_indicator_ids)

            if unassessed.exists():
                # More indicators to assess - continue to next unassessed indicator
                next_indicator = unassessed.order_by('created_at').first()
                if next_indicator:
                    messages.info(request, f'{unassessed.count()} more indicator(s) need assessment.')
                    return redirect('record_indicator_assessment_for_indicator', indicator_id=next_indicator.pk)
            else:
                # All indicators assessed - check if there are controls to assess
                active_controls = Control.objects.filter(risk_id=risk.pk, is_active=True)
                if active_controls.exists():
                    messages.success(request, 'All indicators assessed! Now assess control effectiveness.')
                    return redirect('assess_controls', risk_id=risk.risk_id)
                else:
                    # No controls - proceed to risk assessment
                    messages.success(request, 'All indicators assessed! Please complete the overall risk assessment.')
                    return redirect(f'/risks/{risk.risk_id}/add-assessment/?show_indicator_results=1')
        else:
            logger.debug("Indicator assessment form errors (indicator): %s", form.errors)
    else:
        form = IndicatorAssessmentForm(indicator=indicator, schedule=None)
    
    # Get workflow context
    is_workflow = (request.session.get('workflow_step') == 'assess_indicators' and 
                   request.session.get('new_risk_id') == risk.pk)
    indicators_count = RiskIndicator.objects.filter(risk_id=risk.pk).count()
    assessed_count = IndicatorAssessment.objects.filter(indicator__risk_id=risk.pk).values('indicator').distinct().count()

    context = {
        'form': form,
        'indicator': indicator,
        'risk': risk,
        'schedule': None,
        'form_title': 'Record Indicator Assessment',
        'is_workflow': is_workflow,
        'indicators_count': indicators_count,
        'assessed_count': assessed_count,
    }

    return render(request, 'riskregister/indicator_assessment_form.html', context)


@login_required
def indicator_assessment_history(request, indicator_id):
    """Display assessment history for an indicator with trend analysis"""
    indicator = get_object_or_404(RiskIndicator, pk=indicator_id)
    risk = indicator.risk
    
    # Get all assessments for this indicator (no decision relation — removed)
    assessments_qs = IndicatorAssessment.objects.filter(
        indicator=indicator
    ).select_related(
        'assessed_by'
    ).order_by('-assessment_date')

    # If an `as_of` query param was provided (YYYY-MM-DD), only show assessments
    # that occurred on-or-before that date — useful when drilling into indicator
    # history from a risk assessment to see the snapshot at that time.
    as_of = request.GET.get('as_of')
    filter_label = None
    if as_of:
        try:
            as_of_date = datetime.strptime(as_of, '%Y-%m-%d').date()
            assessments_qs = assessments_qs.filter(assessment_date__lte=as_of_date)
            filter_label = as_of_date
        except Exception:
            # ignore parse errors and show full history
            filter_label = None
    
    # Calculate variance from tolerance for each assessment
    # Return the full (or filtered) history so the template can display the
    # assessments that occurred up to the supplied `as_of` date if provided.
    assessments_list = list(assessments_qs)
    tolerance_variance_map = {}
    for assessment in assessments_list:
        if indicator.trigger_threshold is not None and assessment.measured_value is not None:
            tolerance_variance_map[assessment.pk] = float(assessment.measured_value) - float(indicator.trigger_threshold)
        else:
            tolerance_variance_map[assessment.pk] = None
    
    # Get upcoming schedules
    upcoming_schedules = PeriodicMeasurementSchedule.objects.filter(
        indicator=indicator,
        status='pending',
        scheduled_date__gte=date.today()
    ).order_by('scheduled_date')[:5]
    
    # Get overdue schedules
    overdue_schedules = PeriodicMeasurementSchedule.objects.filter(
        indicator=indicator,
        status='pending',
        scheduled_date__lt=date.today()
    ).order_by('scheduled_date')
    
    # Calculate statistics (use the queryset for counts)
    total_assessments = assessments_qs.count()
    breached_count = assessments_qs.filter(status='breached').count()
    caution_count = assessments_qs.filter(status='caution').count()
    on_target_count = assessments_qs.filter(status='on_target').count()

    # Get latest assessment
    latest = assessments_qs.first()
    
    context = {
        'indicator': indicator,
        'risk': risk,
        'assessments': assessments_list,
        'tolerance_variance_map': tolerance_variance_map,
        'as_of': filter_label,
        'latest_assessment': latest,
        'upcoming_schedules': upcoming_schedules,
        'overdue_schedules': overdue_schedules,
        'total_assessments': total_assessments,
        'breached_count': breached_count,
        'caution_count': caution_count,
        'on_target_count': on_target_count,
    }
    
    return render(request, 'riskregister/indicator_assessment_history.html', context)


@login_required
def generate_indicator_schedules(request, indicator_id):
    """Generate future measurement schedules for an indicator"""
    indicator = get_object_or_404(RiskIndicator, pk=indicator_id)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        num_periods = int(request.POST.get('num_periods', 12))
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = date.today()
        
        # Generate schedules
        schedules = indicator.generate_assessment_schedules(
            start_date=start_date,
            num_periods=num_periods
        )
        
        return redirect('indicator_assessment_history', indicator_id=indicator.pk)
    
    context = {
        'indicator': indicator,
        'risk': indicator.risk,
    }
    
    return render(request, 'riskregister/generate_schedules_form.html', context)


@login_required
def add_indicator(request, risk_id):
    """Add a `RiskIndicator` to a given risk."""
    # Try parsing formatted risk identifier like 'R01OP' into a (risk_number, dept_abbr)
    # and query by those fields. If that fails, fall back to numeric PK extraction
    # to support legacy numeric URLs.
    risk = None
    numeric_id = None
    rid = str(risk_id)
    m = re.match(r"R?(?P<num>\d+)(?P<dept>[A-Za-z]+)$", rid)
    if m:
        num = int(m.group('num'))
        dept_abbr = m.group('dept')
        try:
            risk = Risk.objects.get(risk_number=num, department__abbreviation__iexact=dept_abbr)
            numeric_id = risk.pk  # Set numeric_id for workflow check
        except Risk.DoesNotExist:
            risk = None

    if risk is None:
        # Fallback: extract first numeric substring and treat as PK
        numbers = re.findall(r'\d+', rid)
        if not numbers:
            raise Http404("No Risk matches the given query.")
        numeric_id = int(numbers[0])
        risk = get_object_or_404(Risk, pk=numeric_id)
    
    # Check if this is part of the new risk workflow
    is_workflow = request.session.get('workflow_step') == 'add_indicators' and request.session.get('new_risk_id') == numeric_id

    if request.method == 'POST':
        # If an existing indicator form was submitted, handle it first
        existing_pk = request.POST.get('existing_indicator_pk')
        if existing_pk:
            try:
                existing_ind = RiskIndicator.objects.get(pk=int(existing_pk), risk_id=risk.pk)
            except (RiskIndicator.DoesNotExist, ValueError):
                messages.error(request, 'Indicator not found.')
                return redirect('add_indicator', risk_id=risk.risk_id)

            prefix = f"existing_{existing_ind.pk}"
            existing_form = RiskIndicatorForm(request.POST, instance=existing_ind, prefix=prefix)
            if existing_form.is_valid():
                existing_form.save()
                messages.success(request, f'Indicator #{existing_ind.pk} updated successfully.')
            else:
                # If invalid, re-render the page with the invalid form displayed in context below
                messages.error(request, 'Please correct the errors in the indicator form.')
                form = RiskIndicatorForm()  # new-add form
                # Prepare existing_indicator_forms including this invalid one so errors show
                existing_indicators = list(RiskIndicator.objects.filter(risk_id=risk.pk).order_by('created_at'))
                existing_indicator_forms = []
                for ind in existing_indicators:
                    if ind.pk == existing_ind.pk:
                        existing_indicator_forms.append(existing_form)
                    else:
                        existing_indicator_forms.append(RiskIndicatorForm(instance=ind, prefix=f"existing_{ind.pk}"))

                context = {
                    'form': form,
                    'risk': risk,
                    'page_title': 'Add Indicator',
                    'is_workflow': is_workflow,
                    'existing_indicators_count': len(existing_indicators),
                    'existing_indicators': existing_indicators,
                    'existing_indicator_forms': existing_indicator_forms,
                }
                return render(request, 'riskregister/indicator_form.html', context)

            return redirect('add_indicator', risk_id=risk.risk_id)

        # Otherwise, handle creation of a new indicator
        form = RiskIndicatorForm(request.POST)
        action = request.POST.get('action', 'save')  # 'save' or 'save_and_add_more'

        if form.is_valid():
            indicator = form.save(commit=False)
            indicator.risk = risk
            indicator.created_by = request.user if request.user.is_authenticated else None
            indicator.save()
            messages.success(request, f'Indicator added successfully!')

            if action == 'save_and_add_more':
                # Stay on the same page to add more indicators
                return redirect('add_indicator', risk_id=risk.risk_id)
            elif is_workflow:
                # Part of new risk workflow - check if user wants to proceed to assessment
                if request.POST.get('proceed_to_assessment'):
                    # Update workflow step
                    request.session['workflow_step'] = 'assess_indicators'
                    messages.info(request, 'Now assess the indicators you just added to complete the risk evaluation.')
                    # Redirect to first indicator assessment
                    indicators = RiskIndicator.objects.filter(risk_id=risk.pk).order_by('created_at')
                    first_indicator = indicators.first()
                    if first_indicator:
                        return redirect('record_indicator_assessment_for_indicator', indicator_id=first_indicator.pk)
                    else:
                        return redirect('risk_detail', risk_id=risk.risk_id)
                else:
                    # Continue adding more indicators
                    return redirect('add_indicator', risk_id=risk.risk_id)
            else:
                # Normal flow - redirect to risk detail
                return redirect('risk_detail', risk_id=risk.risk_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RiskIndicatorForm()

    # Get existing indicators and count for display
    existing_indicators = list(RiskIndicator.objects.filter(risk_id=risk.pk).order_by('created_at'))
    existing_indicators_count = len(existing_indicators)

    # Instantiate a RiskIndicatorForm for each existing indicator (pre-filled)
    existing_indicator_forms = [RiskIndicatorForm(instance=ind, prefix=f"existing_{ind.pk}") for ind in existing_indicators]

    context = {
        'form': form,
        'risk': risk,
        'page_title': 'Add Indicator',
        'is_workflow': is_workflow,
        'existing_indicators_count': existing_indicators_count,
        'existing_indicators': existing_indicators,
        'existing_indicator_forms': existing_indicator_forms,
    }
    return render(request, 'riskregister/indicator_form.html', context)

@login_required
def actions_dashboard(request):
    """
    Comprehensive actions dashboard showing all upcoming, scheduled, and overdue activities
    """
    today = date.today()
    seven_days = today + timedelta(days=7)
    fifteen_days = today + timedelta(days=15)
    ninety_days_ago = today - timedelta(days=90)
    
    # OVERDUE MITIGATIONS
    overdue_mitigations = Mitigation.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'in_progress']
    ).select_related('risk', 'risk__department', 'responsible_person').order_by('due_date')
    
    # Calculate days overdue
    overdue_days_map = {}
    for mitigation in overdue_mitigations:
        if mitigation.due_date:
            overdue_days_map[mitigation.pk] = (today - mitigation.due_date).days
    
    # OVERDUE INDICATOR MEASUREMENTS
    overdue_indicators = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__lt=today,
        status='pending'
    ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    # Calculate days overdue for schedules
    overdue_indicators_days_map = {}
    for schedule in overdue_indicators:
        if schedule.scheduled_date:
            overdue_indicators_days_map[schedule.pk] = (today - schedule.scheduled_date).days

    # Convert QuerySets to lists to ensure counts match rendered items
    overdue_mitigations = list(overdue_mitigations)
    overdue_indicators = list(overdue_indicators)
    
    # PENDING ASSESSMENTS - Risks without any assessments
    risks_no_assessment = Risk.objects.filter(
        assessments__isnull=True
    ).select_related('department', 'risk_owner')
    
    # Placeholder for pending assessments (if you have a specific model/field)
    pending_assessments = []
    
    # UPCOMING ASSESSMENTS (Next 15 Days)
    assessments_due_soon = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__gte=today,
        scheduled_date__lte=fifteen_days,
        status='pending'
    ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    # Calculate days until due for schedules
    assessments_days_until_map = {}
    for schedule in assessments_due_soon:
        if schedule.scheduled_date:
            assessments_days_until_map[schedule.pk] = (schedule.scheduled_date - today).days
    
    # UPCOMING RISK REVIEWS (last assessed > 90 days ago)
    risks_with_old_assessments = Risk.objects.annotate(
        last_assessment=Max('assessments__assessment_date')
    ).filter(
        Q(last_assessment__lt=ninety_days_ago) | Q(last_assessment__isnull=True)
    ).select_related('department', 'risk_owner')
    
    # Get last assessment dates
    risk_assessment_dates = {}
    try:
        from .models import RiskAssessment
        for risk in risks_with_old_assessments:
            latest = RiskAssessment.objects.filter(risk_id=risk.pk).order_by('-assessment_date').first()
            if latest:
                risk_assessment_dates[risk.pk] = latest.assessment_date
            else:
                risk_assessment_dates[risk.pk] = 'Never'
    except ImportError:
        pass
    
    # AT-RISK MITIGATIONS (Due within 7 days, not yet complete)
    at_risk_mitigations = Mitigation.objects.filter(
        due_date__gte=today,
        due_date__lte=seven_days,
        status__in=['pending', 'in_progress']
    ).select_related('risk', 'risk__department', 'responsible_person').order_by('due_date')
    
    # UPCOMING MITIGATIONS (Due within 15 days, on track)
    upcoming_mitigations = Mitigation.objects.filter(
        due_date__gt=seven_days,
        due_date__lte=fifteen_days,
        status__in=['in_progress']
    ).select_related('risk', 'risk__department', 'responsible_person').order_by('due_date')
    
    # BREACHED INDICATORS removed from Actions dashboard (not computed)
    breached_list = []
    
    # CALCULATE SUMMARY COUNTS (use concrete lengths so UI matches rendered lists)
    overdue_count = len(overdue_mitigations) + len(overdue_indicators)
    urgent_count = at_risk_mitigations.count()
    upcoming_count = assessments_due_soon.count() + risks_with_old_assessments.count()
    scheduled_count = upcoming_mitigations.count()
    at_risk_count = at_risk_mitigations.count()
    total_actions = (overdue_count + urgent_count + upcoming_count +
                    scheduled_count + len(list(risks_no_assessment)))
    
    context = {
        'overdue_mitigations': overdue_mitigations,
        'overdue_days_map': overdue_days_map,
        'overdue_indicators': overdue_indicators,
        'overdue_indicators_days_map': overdue_indicators_days_map,
        'risks_no_assessment': risks_no_assessment,
        'pending_assessments': pending_assessments,
        'assessments_due_soon': assessments_due_soon,
        'assessments_days_until_map': assessments_days_until_map,
        'upcoming_reviews': risks_with_old_assessments,
        'risk_assessment_dates': risk_assessment_dates,
        'at_risk_mitigations': at_risk_mitigations,
        'upcoming_mitigations': upcoming_mitigations,
        
        # Summary counts for dashboard
        'overdue_count': overdue_count,
        'urgent_count': urgent_count,
        'upcoming_count': upcoming_count,
        'scheduled_count': scheduled_count,
        'at_risk_count': at_risk_count,
        'total_actions': total_actions,
    }
    
    return render(request, 'riskregister/actions_dashboard.html', context)


# Risk Approval and Management Views
@login_required
@user_passes_test(is_superuser)
def approve_risk(request, risk_id):
    """Approve a pending risk (superuser only)"""
    risk = get_object_or_404(Risk, pk=risk_id)
    
    # Allow approving risks that are pending or previously rejected
    if risk.status not in ('pending', 'rejected'):
        messages.error(request, 'Only pending or rejected risks can be approved.')
        return redirect('home')
    
    risk.approve(user=request.user)
    messages.success(request, f'Risk {risk.risk_id} has been approved successfully.')
    
    return redirect('risk_detail', risk_id=risk.risk_id)


@login_required
@user_passes_test(is_superuser)
def reject_risk(request, risk_id):
    """Reject a pending risk (superuser only)"""
    risk = get_object_or_404(Risk, pk=risk_id)
    
    if risk.status != 'pending':
        messages.error(request, 'Only pending risks can be rejected.')
        return redirect('home')
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', 'No reason provided')
        risk.reject(user=request.user, reason=reason)
        messages.warning(request, f'Risk {risk.risk_id} has been rejected.')
        return redirect('home')
    
    return render(request, 'riskregister/reject_confirm.html', {'risk': risk})


@login_required
def submit_risk(request, risk_id):
    """Submit a parked risk for approval (staff user)"""
    risk = get_object_or_404(Risk, pk=risk_id)
    
    # Check if user is the creator or a superuser
    if risk.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'You can only submit risks you created.')
        return redirect('home')
    
    if risk.status != 'parked':
        messages.error(request, 'Only parked risks can be submitted for approval.')
        return redirect('risk_detail', risk_id=risk.risk_id)
    
    risk.submit_for_approval()
    messages.success(request, f'Risk {risk.risk_id} has been submitted for approval.')
    
    return redirect('risk_detail', risk_id=risk.risk_id)


@login_required
@user_passes_test(is_superuser)
def soft_delete_risk(request, risk_id):
    """Soft delete an approved risk (superuser only)"""
    risk = get_object_or_404(Risk, pk=risk_id)
    
    if risk.status != 'approved':
        messages.error(request, 'Only approved risks can be soft deleted.')
        return redirect('home')
    
    if request.method == 'POST':
        risk.soft_delete(user=request.user)
        messages.info(request, f'Risk {risk.risk_id} has been deleted.')
        return redirect('home')
    
    return render(request, 'riskregister/delete_confirm.html', {'risk': risk})


@login_required
@user_passes_test(is_superuser)
def restore_risk(request, risk_id):
    """Restore a soft deleted risk (superuser only)"""
    risk = get_object_or_404(Risk.all_objects, pk=risk_id)
    
    if not risk.is_deleted:
        messages.error(request, 'This risk is not deleted.')
        return redirect('home')
    
    risk.restore()
    messages.success(request, f'Risk {risk.risk_id} has been restored.')
    
    return redirect('risk_detail', risk_id=risk.risk_id)


# Workflow Views
@login_required
def parked_risks(request):
    """View all parked/draft risks"""
    user = request.user
    
    if user.is_superuser:
        # Superuser sees all parked risks
        risks = Risk.objects.filter(status='parked').select_related('department', 'risk_owner', 'category', 'created_by').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-created_at')
    else:
        # Staff users see only their own parked risks
        risks = Risk.objects.filter(status='parked', created_by=user).select_related('department', 'risk_owner', 'category').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-created_at')
    
    context = {
        'risks': risks,
        'total_count': risks.count(),
        'page_title': 'Parked/Draft Risks',
        'status_filter': 'parked',
    }
    
    return render(request, 'riskregister/workflow_risks.html', context)


@login_required
def global_dashboard(request):
    """Global Dashboard: aggregate data for charts."""
    import json
    from django.db.models import Count

    # Risks by category
    risks_by_category_qs = Risk.objects.values('category__name').annotate(count=Count('id')).order_by('-count')
    categories = [r['category__name'] for r in risks_by_category_qs]
    category_counts = [r['count'] for r in risks_by_category_qs]

    # Risks by owner (include 'Unassigned')
    risks_by_owner_qs = Risk.objects.values('risk_owner__name').annotate(count=Count('id')).order_by('-count')
    owners = [r['risk_owner__name'] or 'Unassigned' for r in risks_by_owner_qs]
    owner_counts = [r['count'] for r in risks_by_owner_qs]

    # Mitigation status counts
    mitigation_status_qs = Mitigation.objects.values('status').annotate(count=Count('id'))
    mitigation_labels = [m['status'] for m in mitigation_status_qs]
    mitigation_counts = [m['count'] for m in mitigation_status_qs]

    # Caution / Breach / OK counts based on risk score thresholds
    # Using SQL expression for score multiplication for simplicity with SQLite
    breach_count = Risk.objects.filter(likelihood__isnull=False, impact__isnull=False).extra(where=["(likelihood*impact) >= 15"]).count()
    caution_count = Risk.objects.filter(likelihood__isnull=False, impact__isnull=False).extra(where=["(likelihood*impact) >= 8 AND (likelihood*impact) < 15"]).count()
    ok_count = Risk.objects.filter(likelihood__isnull=False, impact__isnull=False).extra(where=["(likelihood*impact) < 8"]).count()

    context = {
        'categories_json': json.dumps(categories),
        'category_counts_json': json.dumps(category_counts),
        'owners_json': json.dumps(owners),
        'owner_counts_json': json.dumps(owner_counts),
        'mitigation_labels_json': json.dumps(mitigation_labels),
        'mitigation_counts_json': json.dumps(mitigation_counts),
        'breach_count': breach_count,
        'caution_count': caution_count,
        'ok_count': ok_count,
    }
    # Also compute weighted aggregated risk metrics for the statistics page
    from .models import RiskCategory
    approved_risks = Risk.objects.filter(status='approved').select_related('category')
    category_weighted_stats = []
    weighted_numerator = 0.0
    weighted_denominator = 0.0
    total_risks = approved_risks.count()

    for cat in RiskCategory.objects.all():
        cat_qs = approved_risks.filter(category=cat)
        cat_count = cat_qs.count()
        if cat_count == 0:
            total_score = 0
            avg_score = 0.0
        else:
            total_score = sum(getattr(r, 'risk_score', 0) for r in cat_qs)
            avg_score = float(total_score) / cat_count if cat_count > 0 else 0.0

        cat_weight = float(getattr(cat, 'weight', 5) or 5)
        cat_weighted_score = avg_score * (cat_weight / 10.0)

        weighted_numerator += avg_score * cat_count * cat_weight
        weighted_denominator += cat_count * cat_weight

        category_weighted_stats.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'count': cat_count,
            'total_score': total_score,
            'average_score': round(avg_score, 2),
            'weight': int(cat_weight),
            'weighted_score': round(cat_weighted_score, 2),
            'avg_pct': round((avg_score / 25.0) * 100, 2) if 25.0 > 0 else 0.0,
            'weighted_pct': round((cat_weighted_score / 25.0) * 100, 2) if 25.0 > 0 else 0.0,
        })

    overall_weighted_average = round((weighted_numerator / weighted_denominator), 2) if weighted_denominator > 0 else 0.0
    overall_weighted_total = round(overall_weighted_average * total_risks, 2) if total_risks > 0 else 0.0

    # add weighted metrics to context
    context.update({
        'category_weighted_stats': category_weighted_stats,
        'overall_weighted_average': overall_weighted_average,
        'overall_weighted_total': overall_weighted_total,
    })
    return render(request, 'riskregister/global_dashboard.html', context)


@login_required
def pending_risks(request):
    """View all pending risks awaiting approval"""
    user = request.user
    
    if user.is_superuser:
        # Superuser sees all pending risks
        qs = Risk.objects.filter(status='pending').select_related('department', 'risk_owner', 'category', 'created_by').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-created_at')
    else:
        # Staff users see only their own pending risks
        qs = Risk.objects.filter(status='pending', created_by=user).select_related('department', 'risk_owner', 'category').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-created_at')

    paginator = Paginator(qs, 10)
    risks_page = paginator.get_page(request.GET.get('page'))

    context = {
        'risks': risks_page,
        'total_count': qs.count(),
        'page_title': 'Pending Approval',
        'status_filter': 'pending',
    }
    
    return render(request, 'riskregister/workflow_risks.html', context)


@login_required
def approved_risks(request):
    """View all approved risks"""
    risks = Risk.objects.filter(status='approved').select_related('department', 'risk_owner', 'category', 'approved_by').annotate(
        score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
    ).order_by('-approved_at')
    
    context = {
        'risks': risks,
        'total_count': risks.count(),
        'page_title': 'Approved Risks',
        'status_filter': 'approved',
    }
    
    return render(request, 'riskregister/workflow_risks.html', context)


@login_required
def rejected_risks(request):
    """View all rejected risks with feedback"""
    user = request.user
    
    if user.is_superuser:
        # Superuser sees all rejected risks
        risks = Risk.objects.filter(status='rejected').select_related('department', 'risk_owner', 'category', 'created_by', 'approved_by').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-approved_at')
    else:
        # Staff users see only their own rejected risks
        risks = Risk.objects.filter(status='rejected', created_by=user).select_related('department', 'risk_owner', 'category', 'approved_by').annotate(
            score=ExpressionWrapper(F('likelihood') * F('impact'), output_field=IntegerField())
        ).order_by('-approved_at')
    
    context = {
        'risks': risks,
        'total_count': risks.count(),
        'page_title': 'Rejected Risks',
        'status_filter': 'rejected',
    }
    
    return render(request, 'riskregister/workflow_risks.html', context)


@login_required
def generate_risk_pdf_report(request):
    """
    Generate and download a PDF report of risks based on filters.
    """
    # Get filter parameters from request
    department = request.GET.get('department')
    category = request.GET.get('category')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    risks = Risk.objects.select_related(
        'department', 'category', 'risk_owner', 'created_by'
    ).prefetch_related('mitigations').annotate(
        score=ExpressionWrapper(
            F('likelihood') * F('impact'),
            output_field=IntegerField()
        )
    )
    
    # Apply filters
    filters_applied = {}
    
    if department:
        risks = risks.filter(department_id=department)
        dept_obj = Department.objects.filter(id=department).first()
        filters_applied['Department'] = dept_obj.name if dept_obj else department
    
    if category:
        risks = risks.filter(category_id=category)
        cat_obj = RiskCategory.objects.filter(id=category).first()
        filters_applied['Category'] = cat_obj.name if cat_obj else category
    
    if status:
        risks = risks.filter(status=status)
        filters_applied['Status'] = status.title()
    
    if priority:
        # Filter by risk score/priority
        if priority == 'critical':
            risks = risks.filter(score__gte=20)
        elif priority == 'high':
            risks = risks.filter(score__gte=15, score__lt=20)
        elif priority == 'medium':
            risks = risks.filter(score__gte=8, score__lt=15)
        elif priority == 'low':
            risks = risks.filter(score__lt=8)
        filters_applied['Priority'] = priority.title()
    
    if date_from:
        risks = risks.filter(created_at__gte=date_from)
        filters_applied['Date From'] = date_from
    
    if date_to:
        risks = risks.filter(created_at__lte=date_to)
        filters_applied['Date To'] = date_to
    
    # Order by score descending (highest risk first)
    # `risk_id` is a Python property (not a DB field). Use real model fields for ORM ordering.
    risks = risks.order_by('-score', 'department__name', 'risk_number')
    
    # Generate PDF
    try:
        filepath, filename = generate_risk_report_pdf(risks, filters_applied)
        
        # Serve the PDF file
        response = FileResponse(
            open(filepath, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def generate_detailed_risk_pdf_report(request):
    """
    Generate and download a detailed PDF report with full risk information.
    """
    # Get risk IDs from request (for specific risks) or use filters
    risk_ids = request.GET.getlist('risk_ids[]')
    
    if risk_ids:
        risks = Risk.objects.filter(id__in=risk_ids)
    else:
        # Use same filters as simple report
        risks = Risk.objects.select_related(
            'department', 'category', 'risk_owner'
        ).prefetch_related('mitigations').annotate(
            score=ExpressionWrapper(
                F('likelihood') * F('impact'),
                output_field=IntegerField()
            )
        )
        
        # Apply filters (same as above)
        status = request.GET.get('status', 'approved')
        risks = risks.filter(status=status)
    
    risks = risks.order_by('-created_at')
    
    try:
        filepath, filename = generate_detailed_risk_report_pdf(risks)
        
        response = FileResponse(
            open(filepath, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Exception as e:
        return HttpResponse(f"Error generating detailed PDF: {str(e)}", status=500)


@login_required
def risk_report_options(request):
    """
    Display page with options to generate various risk reports.
    """
    departments = Department.objects.all()
    categories = RiskCategory.objects.all()
    
    context = {
        'departments': departments,
        'categories': categories,
        'page_title': 'Generate Risk Reports',
    }
    
    return render(request, 'riskregister/report_options.html', context)


# Notification functionality removed. If you need to reintroduce notifications,
# implement views/utilities and register URLs/templates again.

@login_required
def risk_assessment_detail(request, assessment_id):
    """
    Display detailed view of a risk assessment with full traceability to source indicator assessments
    """
    assessment = get_object_or_404(RiskAssessment, id=assessment_id)
    risk = assessment.risk
    
    # Get source indicator assessments grouped by status
    source_assessments = assessment.source_indicator_assessments.select_related(
        'indicator', 'assessed_by'
    ).order_by('-status', '-assessment_date')
    
    # Group by status for better display
    breached = source_assessments.filter(status='breached')
    caution = source_assessments.filter(status='caution')
    on_target = source_assessments.filter(status='on_target')
    
    # Get previous assessment for comparison
    previous_assessment = RiskAssessment.objects.filter(
        risk=risk,
        assessment_date__lt=assessment.assessment_date
    ).order_by('-assessment_date').first()
    
    # Calculate trends if previous assessment exists
    likelihood_trend = None
    impact_trend = None
    if previous_assessment:
        likelihood_trend = 'up' if assessment.likelihood > previous_assessment.likelihood else (
            'down' if assessment.likelihood < previous_assessment.likelihood else 'same'
        )
        impact_trend = 'up' if assessment.impact > previous_assessment.impact else (
            'down' if assessment.impact < previous_assessment.impact else 'same'
        )
    
    # Get assessment history
    assessment_history = RiskAssessment.objects.filter(
        risk=risk
    ).order_by('-assessment_date')[:10]
    
    # Get linked indicators breakdown (new requirement)
    linked_indicators = [ia.indicator for ia in source_assessments]
    can_complete, completion_message = assessment.can_be_completed()
    
    context = {
        'assessment': assessment,
        'risk': risk,
        'breached_assessments': breached,
        'caution_assessments': caution,
        'on_target_assessments': on_target,
        'previous_assessment': previous_assessment,
        'likelihood_trend': likelihood_trend,
        'impact_trend': impact_trend,
        'assessment_history': assessment_history,
        'has_sources': source_assessments.exists(),
        'linked_indicators': linked_indicators,
        'indicator_breakdown': assessment.get_indicator_breakdown(),
        'can_complete': can_complete,
        'completion_message': completion_message,
    }
    
    return render(request, 'riskregister/risk_assessment_detail.html', context)


@login_required
def assessment_dashboard(request):
    """
    Comprehensive assessment dashboard showing calendar, trends, and status
    """
    from dateutil.relativedelta import relativedelta
    from django.db.models import Count, Q
    
    today = date.today()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(days=1)
    
    # Get upcoming assessments
    upcoming_schedules = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__gte=today,
        scheduled_date__lte=today + timedelta(days=30),
        status='pending'
    ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    # Get overdue assessments
    overdue_schedules = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__lt=today,
        status__in=['pending', 'overdue']
    ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    # Get recent assessments
    recent_assessments = IndicatorAssessment.objects.select_related(
        'indicator', 'indicator__risk', 'assessed_by'
    ).order_by('-assessment_date')[:20]
    
    # Get recent risk assessments
    recent_risk_assessments = RiskAssessment.objects.select_related(
        'risk', 'assessor'
    ).order_by('-assessment_date')[:10]
    
    # Assessment completion stats
    this_month_completed = IndicatorAssessment.objects.filter(
        assessment_date__gte=start_of_month,
        assessment_date__lte=end_of_month
    ).count()
    
    this_month_scheduled = PeriodicMeasurementSchedule.objects.filter(
        scheduled_date__gte=start_of_month,
        scheduled_date__lte=end_of_month
    ).count()
    
    completion_rate = (
        (this_month_completed / this_month_scheduled * 100) 
        if this_month_scheduled > 0 else 0
    )
    
    # Status breakdown
    status_breakdown = IndicatorAssessment.objects.filter(
        assessment_date__gte=today - timedelta(days=90)
    ).values('status').annotate(count=Count('id'))
    
    # Prepare traceability matrix data
    risks_with_indicators = Risk.objects.filter(
        status__in=['approved', 'active']
    ).prefetch_related('indicators').annotate(
        indicator_count=Count('indicators'),
        recent_assessments_count=Count(
            'indicators__assessments',
            filter=Q(indicators__assessments__assessment_date__gte=today - timedelta(days=30))
        )
    )
    
    context = {
        'upcoming_schedules': upcoming_schedules,
        'overdue_schedules': overdue_schedules,
        'recent_assessments': recent_assessments,
        'recent_risk_assessments': recent_risk_assessments,
        'this_month_completed': this_month_completed,
        'this_month_scheduled': this_month_scheduled,
        'completion_rate': completion_rate,
        'status_breakdown': status_breakdown,
        'risks_with_indicators': risks_with_indicators,
        'today': today,
    }
    
    return render(request, 'riskregister/assessment_dashboard.html', context)


@login_required
def assess_controls(request, risk_id):
    """Assess control effectiveness for a risk"""
    # Resolve risk
    rid = str(risk_id)
    m = re.match(r"R?(?P<num>\d+)(?P<dept>[A-Za-z]+)$", rid)
    risk = None
    if m:
        num = int(m.group('num'))
        dept_abbr = m.group('dept')
        try:
            risk = Risk.objects.get(risk_number=num, department__abbreviation__iexact=dept_abbr)
        except Risk.DoesNotExist:
            risk = None

    if risk is None:
        numbers = re.findall(r'\d+', rid)
        if not numbers:
            messages.error(request, 'Invalid risk ID format')
            return redirect('all_risks')
        numeric_id = int(numbers[0])
        try:
            risk = Risk.objects.get(pk=numeric_id)
        except Risk.DoesNotExist:
            messages.error(request, 'Risk not found')
            return redirect('all_risks')
    
    # Get active controls
    controls = Control.objects.filter(risk_id=risk.pk, is_active=True).order_by('id')
    
    if request.method == 'POST':
        # Process control effectiveness ratings
        all_updated = True
        for control in controls:
            effectiveness_key = f'control_effectiveness_{control.pk}'
            if effectiveness_key in request.POST:
                try:
                    effectiveness = Decimal(request.POST[effectiveness_key])
                    if 0 <= effectiveness <= 100:
                        control.effectiveness = effectiveness
                        control.save(update_fields=['effectiveness'])
                    else:
                        all_updated = False
                        messages.warning(request, f'Invalid effectiveness value for control: {control.name}')
                except (ValueError, InvalidOperation):
                    all_updated = False
                    messages.warning(request, f'Invalid effectiveness value for control: {control.name}')
        
        if all_updated:
            messages.success(request, 'Control effectiveness assessed! Please complete the overall risk assessment.')
            return redirect('add_assessment', risk_id=risk.risk_id)
    
    context = {
        'risk': risk,
        'controls': controls,
        'form_title': 'Assess Control Effectiveness'
    }
    
    return render(request, 'riskregister/assess_controls.html', context)


@login_required
def my_activities(request):
    # `my_activities` view removed per request. If you need to restore it,
    # reintroduce the function implementation here or point the URL to an
    # alternative view. For now, return 404 to indicate the page is gone.
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound('My Activities page has been removed.')


@login_required
def notification_preferences(request):
    """Allow users to configure their notification preferences and send a test email."""
    from django.http import HttpResponseNotFound
    # Only superusers may access notification preference forms via the UI
    if not request.user.is_superuser:
        return HttpResponseNotFound('Notification preferences are admin-only.')
    from .models import NotificationPreference
    from .forms import NotificationPreferenceForm, AdminNotificationPreferenceForm
    from .utils.notifications import send_notifications_for_user

    # Admins may edit other users by supplying ?user=<username_or_email>
    target_identifier = request.GET.get('user') if request.user.is_superuser else None
    if request.user.is_superuser and target_identifier:
        # resolve by email or username
        from django.contrib.auth import get_user_model
        User = get_user_model()
        tuser = User.objects.filter(email__iexact=target_identifier).first() or User.objects.filter(username__iexact=target_identifier).first()
        if not tuser:
            messages.error(request, f'No user found for "{target_identifier}"')
            return redirect('notification_preferences')
        pref, _ = NotificationPreference.objects.get_or_create(user=tuser)
        target_user = tuser
    else:
        # Non-superusers are already blocked above, but keep logic consistent
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        target_user = request.user

    if request.method == 'POST':
        form_cls = AdminNotificationPreferenceForm if request.user.is_superuser else NotificationPreferenceForm
        form = form_cls(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences saved.')
            return redirect('notification_preferences')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form_cls = AdminNotificationPreferenceForm if request.user.is_superuser else NotificationPreferenceForm
        form = form_cls(instance=pref)

    template = 'riskregister/notification_preferences.html'
    return render(request, template, {'form': form, 'pref': pref, 'target_user': target_user})


@login_required
def notification_test_send(request):
    """Send a test notification email to the current user (honours preferences visually).

    The actual send uses the configured email backend. For development set
    `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` so output
    appears in the server terminal.
    """
    from .utils.notifications import send_notifications_for_user

    # Use console email backend for test sends so output appears in server terminal
    # Use the project's configured email backend (from settings). For local
    # development you can set `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`.
    conn = None

    from django.http import HttpResponseNotFound
    # Only superusers may trigger test sends via the UI
    if not request.user.is_superuser:
        return HttpResponseNotFound('Test notifications are admin-only.')

    # For superusers, produce an aggregated staff summary
    from .utils.notifications import notify_staff_of_outstanding_items
    notify_staff_of_outstanding_items(connection=conn, include_details=True)
    return redirect('notification_preferences')
