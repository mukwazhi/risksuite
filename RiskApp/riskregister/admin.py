from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Department, RiskCategory, RiskOwner, Risk, Mitigation, MitigationProgressLog, KPI, 
    RiskIndicator, IndicatorMeasurement, PeriodicMeasurementSchedule,
    RiskAssessment, ActivityLog, RiskCategoryImpact, Control
)
from django.db.models import Avg, Count
from django.shortcuts import render
from django.urls import path

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'abbreviation')
    search_fields = ('name', 'abbreviation')
    ordering = ('name',)
    list_per_page = 50

@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)
    list_per_page = 50

@admin.register(RiskOwner)
class RiskOwnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone_number', 'department')
    search_fields = ('name', 'email')
    list_filter = ('department',)
    ordering = ('name',)
    list_per_page = 50

@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'unit', 'direction', 'measurement_period', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('direction', 'measurement_period')
    ordering = ('name',)
    list_per_page = 50
    readonly_fields = ('created_at', 'updated_at')

class MitigationInline(admin.TabularInline):
    model = Mitigation
    extra = 0
    fields = ('strategy', 'action', 'responsible_person', 'due_date', 'status')
    show_change_link = True

class ControlInline(admin.TabularInline):
    model = Control
    extra = 1
    fields = ('name', 'control_type', 'effectiveness', 'weight', 'control_owner', 'is_active')
    show_change_link = True
    classes = ('collapse',)

class IndicatorMeasurementInline(admin.TabularInline):
    model = IndicatorMeasurement
    extra = 1
    fields = ('measured_at', 'value', 'notes', 'status')
    readonly_fields = ('status', 'created_at')
    ordering = ('-measured_at',)

class RiskIndicatorInline(admin.StackedInline):
    model = RiskIndicator
    extra = 0
    fields = (
        ('appetite_level', 'appetite_tolerance_pct', 'active'),
        ('preferred_kpi', 'preferred_kpi_name'),
        ('unit', 'data_source'),
        ('aggregation_method', 'measurement_period', 'direction'),
        ('trigger_threshold', 'trigger_operator'),
        ('breach_threshold', 'breach_operator'),
        'escalation_actions',
        ('order', 'created_by'),
        'notes',
    )
    readonly_fields = ('created_by', 'created_at')
    can_delete = True
    classes = ('collapse',)

class RiskCategoryImpactInline(admin.TabularInline):
    model = RiskCategoryImpact
    extra = 0
    fields = ('category', 'impact', 'likelihood', 'notes')
    show_change_link = True

@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = (
        'risk_id',
        'title',
        'department',
        'category',
        'risk_number',
        'risk_rating',
        'likelihood',
        'impact',
        'risk_owner',
        'is_approved',
        'park_risk',
        'is_deleted',
    )
    list_filter = ('department', 'category', 'likelihood', 'impact', 'is_approved', 'park_risk', 'is_deleted')
    search_fields = ('title', 'description', 'cause', 'impact_description', 'risk_owner__name')
    readonly_fields = ('risk_id', 'risk_rating', 'approved_at', 'approved_by', 'deleted_at', 'deleted_by')
    ordering = ('department', 'risk_number')
    list_select_related = ('department', 'category', 'risk_owner', 'approved_by', 'deleted_by', 'linked_kpi')
    list_per_page = 25
    fieldsets = (
        ('Basic Information', {
            'fields': ('department', 'category', 'risk_number', 'risk_id', 'title', 'description')
        }),
        ('Inherent Risk Assessment (Without Controls)', {
            'fields': ('inherent_likelihood', 'inherent_impact'),
            'description': 'Rate the risk as if no controls existed'
        }),
        ('Current Risk Assessment', {
            'fields': ('cause', 'impact_description', 'likelihood', 'impact', 'risk_rating', 'risk_owner')
        }),
        ('KPI Link', {
            'fields': ('linked_kpi',),
            'classes': ('collapse',)
        }),
        ('Workflow Status', {
            'fields': ('park_risk', 'is_approved', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Deletion Status', {
            'fields': ('is_deleted', 'deleted_by', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [RiskCategoryImpactInline, ControlInline, RiskIndicatorInline, MitigationInline]

    def get_queryset(self, request):
        # Show all risks including soft-deleted in admin
        return Risk.all_objects.select_related('department', 'category', 'risk_owner', 'approved_by', 'deleted_by')

    actions = ['soft_delete_selected', 'restore_selected', 'approve_selected', 'unapprove_selected']

    @admin.action(description='Soft delete selected risks')
    def soft_delete_selected(self, request, queryset):
        for risk in queryset:
            risk.soft_delete(user=request.user)
        self.message_user(request, f"{queryset.count()} risk(s) soft deleted.")

    @admin.action(description='Restore selected risks')
    def restore_selected(self, request, queryset):
        for risk in queryset:
            risk.restore()
        self.message_user(request, f"{queryset.count()} risk(s) restored.")

    @admin.action(description='Approve selected risks')
    def approve_selected(self, request, queryset):
        for risk in queryset:
            risk.approve(user=request.user)
        self.message_user(request, f"{queryset.count()} risk(s) approved.")

    @admin.action(description='Unapprove selected risks')
    def unapprove_selected(self, request, queryset):
        for risk in queryset:
            risk.unapprove()
        self.message_user(request, f"{queryset.count()} risk(s) unapproved.")


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'risk_link',
        'control_type',
        'effectiveness_display',
        'weight',
        'weighted_effectiveness_display',
        'control_owner',
        'is_active',
        'last_tested_date'
    )
    list_filter = ('control_type', 'weight', 'is_active', 'risk__department')
    search_fields = ('name', 'description', 'risk__title', 'risk__risk_number')
    list_select_related = ('risk', 'risk__department', 'control_owner', 'created_by')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'weighted_effectiveness_display')
    ordering = ('-weight', 'control_type', 'name')
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('risk', 'name', 'description', 'control_type')
        }),
        ('Effectiveness & Weight', {
            'fields': (
                ('effectiveness', 'weight'),
                'weight_rationale',
                'weighted_effectiveness_display'
            ),
            'description': 'Set how effective and important this control is'
        }),
        ('Ownership & Testing', {
            'fields': (
                'control_owner',
                'frequency',
                ('last_tested_date', 'test_results')
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def risk_link(self, obj):
        url = reverse('admin:riskregister_risk_change', args=[obj.risk.pk])
        return format_html('<a href="{}">{}</a>', url, obj.risk.risk_id)
    risk_link.short_description = 'Risk'
    
    def effectiveness_display(self, obj):
        color = 'success' if obj.effectiveness >= 70 else 'warning' if obj.effectiveness >= 40 else 'danger'
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color,
            obj.effectiveness
        )
    effectiveness_display.short_description = 'Effectiveness'
    
    def weighted_effectiveness_display(self, obj):
        weighted = obj.weighted_effectiveness
        return f"{weighted:.2f} (Weight: {obj.weight} × Effectiveness: {obj.effectiveness}%)"
    weighted_effectiveness_display.short_description = 'Weighted Contribution'
    
    actions = ['activate_controls', 'deactivate_controls', 'test_reminder']
    
    @admin.action(description='Activate selected controls')
    def activate_controls(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} control(s) activated.")
    
    @admin.action(description='Deactivate selected controls')
    def deactivate_controls(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} control(s) deactivated.")
    
    @admin.action(description='Mark as needing testing')
    def test_reminder(self, request, queryset):
        # This could send notifications or mark controls for testing
        self.message_user(request, f"{queryset.count()} control(s) marked for testing review.")


# --- Admin view: Mitigation progress metrics ---------------------------------
def mitigation_metrics_view(request):
    """Admin view to surface aggregated mitigation progress metrics."""
    total = Mitigation.objects.count()
    by_status = Mitigation.objects.values('status').annotate(count=Count('id')).order_by('-count')
    avg_completion = Mitigation.objects.aggregate(avg=Avg('completion_percentage'))['avg'] or 0
    top_incomplete = Mitigation.objects.exclude(status__iexact='complete').order_by('-completion_percentage')[:10]
    recent_logs = MitigationProgressLog.objects.select_related('mitigation', 'user').order_by('-created_at')[:25]

    context = {
        'title': 'Mitigation Progress Metrics',
        'total_mitigations': total,
        'by_status': list(by_status),
        'avg_completion': round(avg_completion, 2) if avg_completion is not None else 0,
        'top_incomplete': top_incomplete,
        'recent_logs': recent_logs,
    }

    return render(request, 'admin/mitigation_metrics.html', context)


# Inject our view into the admin site URLs
_orig_get_urls = admin.site.get_urls

def get_urls():
    urls = _orig_get_urls()
    my_urls = [path('mitigation-metrics/', admin.site.admin_view(mitigation_metrics_view), name='mitigation-metrics')]
    return my_urls + urls

admin.site.get_urls = get_urls

# Add a link in the admin index by registering a simple ModelAdmin for MitigationMetrics placeholder
class MitigationMetricsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        return mitigation_metrics_view(request)


@admin.register(RiskIndicator)
class RiskIndicatorAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        '__str__',
        'risk', 
        'appetite_level', 
        'active',
        'trigger_info',
        'breach_info',
        'created_at'
    )
    list_filter = ('appetite_level', 'active', 'direction', 'aggregation_method', 'measurement_period')
    search_fields = ('risk__title', 'preferred_kpi__name', 'preferred_kpi_name', 'notes', 'data_source')
    list_select_related = ('risk', 'risk__department', 'preferred_kpi', 'created_by')
    readonly_fields = (
        'created_by', 
        'created_at', 
        'trigger_operator_symbol', 
        'trigger_operator_label',
        'breach_operator_symbol', 
        'breach_operator_label',
        'human_readable_rule'
    )
    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Risk & KPI', {
            'fields': ('risk', 'preferred_kpi', 'preferred_kpi_name', 'unit', 'data_source')
        }),
        ('Evaluation Settings', {
            'fields': (
                ('appetite_level', 'appetite_tolerance_pct'),
                ('aggregation_method', 'measurement_period', 'direction'),
                ('active', 'order')
            )
        }),
        ('Trigger Threshold (Caution)', {
            'fields': (
                ('trigger_threshold', 'trigger_operator', 'trigger_operator_symbol'),
                'trigger_operator_label'
            ),
            'description': 'Set the caution/warning threshold - when measurements reach this level, a caution status is triggered.'
        }),
        ('Breach Threshold (Critical)', {
            'fields': (
                ('breach_threshold', 'breach_operator', 'breach_operator_symbol'),
                'breach_operator_label'
            ),
            'description': 'Set the critical/breach threshold - when measurements reach this level, a breach status is triggered.'
        }),
        ('Summary', {
            'fields': ('human_readable_rule',),
            'classes': ('wide',)
        }),
        ('Escalation & Notes', {
            'fields': ('escalation_actions', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [IndicatorMeasurementInline]
    
    def trigger_info(self, obj):
        if obj.trigger_threshold is not None:
            return f"{obj.trigger_operator_symbol} {obj.trigger_threshold}"
        return "-"
    trigger_info.short_description = "Trigger"
    
    def breach_info(self, obj):
        if obj.breach_threshold is not None:
            return f"{obj.breach_operator_symbol} {obj.breach_threshold}"
        return "-"
    breach_info.short_description = "Breach"

@admin.register(IndicatorMeasurement)
class IndicatorMeasurementAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicator',
        'measured_at',
        'value',
        'status_display',
    )
    list_filter = ('measured_at', 'indicator__risk__department', 'indicator__appetite_level')
    search_fields = ('indicator__preferred_kpi_name', 'indicator__risk__title', 'notes')
    list_select_related = ('indicator', 'indicator__risk', 'indicator__risk__department')
    readonly_fields = ('status', 'created_at')
    ordering = ('-measured_at',)
    date_hierarchy = 'measured_at'
    list_per_page = 50
    
    fieldsets = (
        ('Measurement', {
            'fields': ('indicator', 'measured_at', 'value', 'status')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        status = obj.status
        colors = {
            'ok': 'green',
            'caution': 'orange',
            'breached': 'red',
            'unknown': 'gray',
            'inactive': 'gray'
        }
        color = colors.get(status, 'black')
        return f'<span style="color: {color}; font-weight: bold;">{status.upper()}</span>'
    status_display.short_description = "Status"
    status_display.allow_tags = True

@admin.register(Mitigation)
class MitigationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'risk',
        'strategy',
        'action',
        'responsible_person',
        'due_date',
        'status',
        'completion_percentage',
        'postponement_count',
    )
    list_filter = ('strategy', 'status', 'due_date')
    search_fields = ('risk__title', 'action', 'responsible_person__name')
    ordering = ('-due_date',)
    list_select_related = ('risk', 'risk__department', 'responsible_person')
    list_per_page = 25
    date_hierarchy = 'due_date'
    fields = (
        'risk',
        'strategy',
        'action',
        'responsible_person',
        'due_date',
        'status',
        'completion_percentage',
        'postponement_count',
        'last_postponed_date',
        'original_due_date',
        'evidence',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at', 'postponement_count', 'last_postponed_date')


@admin.register(MitigationProgressLog)
class MitigationProgressLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'mitigation',
        'user',
        'action_type',
        'status_at_time',
        'completion_percentage',
        'created_at',
    )
    list_filter = ('action_type', 'status_at_time', 'created_at')
    search_fields = ('mitigation__action', 'user__username', 'notes')
    ordering = ('-created_at',)
    list_select_related = ('mitigation', 'mitigation__risk', 'user')
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('mitigation', 'user', 'action_type', 'created_at')
        }),
        ('Status Tracking', {
            'fields': (
                'status_at_time',
                'previous_status',
                'completion_percentage',
                'previous_completion_percentage',
            )
        }),
        ('Date Tracking', {
            'fields': ('due_date_at_time', 'previous_due_date')
        }),
        ('Notes and Details', {
            'fields': ('notes', 'evidence')
        }),
        ('Postponement Details', {
            'fields': ('postponement_reason', 'new_target_date'),
            'classes': ('collapse',)
        }),
        ('Failure Details', {
            'fields': ('failure_reason', 'lessons_learned'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PeriodicMeasurementSchedule)
class PeriodicMeasurementScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicator_link',
        'period_type',
        'scheduled_date',
        'status_badge',
        'days_until_due_display',
        'completed_by',
        'reminder_sent',
    )
    list_filter = (
        'status',
        'period_type',
        'scheduled_date',
        'reminder_sent',
        'indicator__risk__department',
    )
    search_fields = (
        'indicator__preferred_kpi_name',
        'indicator__risk__title',
        'notes',
    )
    list_select_related = (
        'indicator',
        'indicator__risk',
        'indicator__risk__department',
        'completed_measurement',
        'completed_by',
    )
    readonly_fields = (
        'is_overdue_display',
        'days_until_due_display_readonly',
        'created_at',
        'updated_at',
    )
    ordering = ('-scheduled_date', 'status')
    date_hierarchy = 'scheduled_date'
    list_per_page = 50
    
    fieldsets = (
        ('Schedule Information', {
            'fields': (
                'indicator',
                'period_type',
                ('start_date', 'end_date'),
                'scheduled_date',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                ('is_overdue_display', 'days_until_due_display_readonly'),
            )
        }),
        ('Completion', {
            'fields': (
                'completed_measurement',
                'completed_at',
                'completed_by',
            ),
            'classes': ('collapse',)
        }),
        ('Reminders', {
            'fields': (
                'reminder_sent',
                'reminder_sent_at',
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_completed',
        'mark_as_skipped',
        'send_reminders',
        'update_status_action',
    ]
    
    def indicator_link(self, obj):
        """Display clickable link to the indicator."""
        url = reverse('admin:riskregister_riskindicator_change', args=[obj.indicator.pk])
        return format_html('<a href="{}">{}</a>', url, obj.indicator)
    indicator_link.short_description = "Indicator"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',      # Yellow
            'completed': '#28a745',    # Green
            'overdue': '#dc3545',      # Red
            'skipped': '#6c757d',      # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def days_until_due_display(self, obj):
        """Display days until due with color coding."""
        days = obj.days_until_due
        if obj.status == 'completed':
            return format_html('<span style="color: green;">✓ Completed</span>')
        elif days < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} days overdue</span>',
                abs(days)
            )
        elif days == 0:
            return format_html('<span style="color: orange; font-weight: bold;">Due today</span>')
        elif days <= 3:
            return format_html(
                '<span style="color: orange;">{} days remaining</span>',
                days
            )
        else:
            return format_html('{} days remaining', days)
    days_until_due_display.short_description = "Due Status"
    
    def is_overdue_display(self, obj):
        """Display is_overdue status safely."""
        if obj.pk is None or obj.scheduled_date is None:
            return "N/A"
        return "Yes" if obj.is_overdue else "No"
    is_overdue_display.short_description = "Is Overdue"

    def days_until_due_display_readonly(self, obj):
        """Display days until due for readonly field."""
        if obj.pk is None or obj.scheduled_date is None:
            return "N/A"
        days = obj.days_until_due
        if days < 0:
            return f"{abs(days)} days overdue"
        elif days == 0:
            return "Due today"
        else:
            return f"{days} days remaining"
    days_until_due_display_readonly.short_description = "Days Until Due"
    
    @admin.action(description='Mark selected schedules as completed')
    def mark_as_completed(self, request, queryset):
        """Mark selected schedules as completed (requires manual measurement creation)."""
        count = 0
        for schedule in queryset.filter(status__in=['pending', 'overdue']):
            # Note: This only changes status. Actual measurement should be created separately
            schedule.status = 'completed'
            schedule.completed_at = timezone.now()
            schedule.completed_by = request.user
            schedule.save()
            count += 1
        
        self.message_user(
            request,
            f"{count} schedule(s) marked as completed. Note: You should create corresponding measurements separately."
        )
    
    @admin.action(description='Mark selected schedules as skipped')
    def mark_as_skipped(self, request, queryset):
        """Mark selected schedules as skipped."""
        count = 0
        for schedule in queryset.filter(status__in=['pending', 'overdue']):
            schedule.mark_skipped(reason="Skipped via admin action")
            count += 1
        
        self.message_user(request, f"{count} schedule(s) marked as skipped.")
    
    @admin.action(description='Send reminders for selected schedules')
    def send_reminders(self, request, queryset):
        """Send reminders for selected schedules."""
        count = 0
        for schedule in queryset.filter(status__in=['pending', 'overdue'], reminder_sent=False):
            if schedule.send_reminder():
                count += 1
        
        self.message_user(request, f"{count} reminder(s) sent.")
    
    @admin.action(description='Update status for selected schedules')
    def update_status_action(self, request, queryset):
        """Update status based on current date."""
        count = 0
        for schedule in queryset:
            old_status = schedule.status
            schedule.update_status()
            if schedule.status != old_status:
                count += 1
        
        self.message_user(request, f"{count} schedule(s) status updated.")

@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'risk_link',
        'assessment_date',
        'assessment_type',
        'likelihood_impact_display',
        'risk_score_display',
        'trend_badge',
        'is_current',
        'assessor',
    )
    list_filter = (
        'assessment_type',
        'assessment_date',
        'is_current',
        'risk__department',
        'likelihood',
        'impact',
    )
    search_fields = (
        'risk__title',
        'risk__risk_id',
        'rationale',
        'changes_since_last',
        'recommendations',
    )
    list_select_related = (
        'risk',
        'risk__department',
        'assessor',
    )
    readonly_fields = (
        'previous_likelihood',  # Make this readonly
        'previous_impact',      # Make this readonly
        'risk_score_readonly',
        'previous_risk_score_readonly',
        'score_change_readonly',
        'trend_readonly',
        'risk_level_readonly',
        'movement_vector_readonly',
        'matrix_position_readonly',
        'movement_description_readonly',
        'created_at',
        'updated_at',
    )
    ordering = ('-assessment_date', '-created_at')
    date_hierarchy = 'assessment_date'
    list_per_page = 50
    
    fieldsets = (
        ('Assessment Information', {
            'fields': (
                'risk',
                'assessment_date',
                'assessment_type',
                'assessor',
                'is_current',
            )
        }),
        ('Current Scores', {
            'fields': (
                ('likelihood', 'impact'),
                ('risk_score_readonly', 'risk_level_readonly'),
                'matrix_position_readonly',
            )
        }),
        ('Previous Scores & Movement (Auto-populated)', {
            'fields': (
                ('previous_likelihood', 'previous_impact'),
                ('previous_risk_score_readonly', 'score_change_readonly'),
                'trend_readonly',
                'movement_vector_readonly',
                'movement_description_readonly',
            ),
            'classes': ('collapse',),
            'description': 'These values are automatically populated from the most recent previous assessment.'
        }),
        ('Assessment Details', {
            'fields': (
                'rationale',
                'changes_since_last',
                'evidence',
                'recommendations',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_current', 'generate_assessment_report']
    
    # Safe readonly field methods
    def risk_score_readonly(self, obj):
        """Display risk score safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A (Enter likelihood and impact)"
        return obj.risk_score
    risk_score_readonly.short_description = "Risk Score"
    
    def previous_risk_score_readonly(self, obj):
        """Display previous risk score safely."""
        if obj.pk is None:
            return "N/A"
        score = obj.previous_risk_score
        return score if score is not None else "N/A (No previous assessment)"
    previous_risk_score_readonly.short_description = "Previous Risk Score"
    
    def score_change_readonly(self, obj):
        """Display score change safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        change = obj.score_change
        if change > 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">+{}</span>', change)
        elif change < 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', change)
        else:
            return "0 (No change)"
    score_change_readonly.short_description = "Score Change"
    
    def trend_readonly(self, obj):
        """Display trend safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        trend = obj.trend
        icons = {
            'improving': '↓ Improving',
            'stable': '→ Stable',
            'deteriorating': '↑ Deteriorating',
            'new': '● New Assessment',
        }
        colors = {
            'improving': '#28a745',
            'stable': '#6c757d',
            'deteriorating': '#dc3545',
            'new': '#007bff',
        }
        icon = icons.get(trend, trend)
        color = colors.get(trend, '#6c757d')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, icon)
    trend_readonly.short_description = "Trend"
    
    def risk_level_readonly(self, obj):
        """Display risk level safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        level = obj.risk_level.title()
        colors = {
            'Critical': '#dc3545',
            'High': '#dc3545',
            'Medium': '#ffc107',
            'Low': '#28a745',
        }
        color = colors.get(level, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, level
        )
    risk_level_readonly.short_description = "Risk Level"
    
    def movement_vector_readonly(self, obj):
        """Display movement vector safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        vector = obj.movement_vector
        if not vector:
            return "No previous assessment"
        
        l_change = vector['likelihood_change']
        i_change = vector['impact_change']
        s_change = vector['score_change']
        
        l_arrow = '↑' if l_change > 0 else ('↓' if l_change < 0 else '→')
        i_arrow = '↑' if i_change > 0 else ('↓' if i_change < 0 else '→')
        
        return format_html(
            'Likelihood: {} {}, Impact: {} {}, Total Score: {:+d}',
            l_arrow, l_change, i_arrow, i_change, s_change
        )
    movement_vector_readonly.short_description = "Movement Vector"
    
    def matrix_position_readonly(self, obj):
        """Display matrix position safely."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        pos = obj.matrix_position
        return f"Likelihood: {pos['likelihood']}, Impact: {pos['impact']} → Score: {pos['score']} ({pos['level'].title()})"
    matrix_position_readonly.short_description = "Matrix Position"
    
    def movement_description_readonly(self, obj):
        """Display human-readable movement description."""
        if obj.pk is None or obj.likelihood is None or obj.impact is None:
            return "N/A"
        return obj.get_movement_description()
    movement_description_readonly.short_description = "Movement Description"
    
    def risk_link(self, obj):
        """Display clickable link to the risk."""
        if obj.risk:
            url = reverse('admin:riskregister_risk_change', args=[obj.risk.pk])
            return format_html('<a href="{}">{}</a>', url, obj.risk.risk_id)
        return "-"
    risk_link.short_description = "Risk"
    
    def likelihood_impact_display(self, obj):
        """Display likelihood and impact."""
        if obj.likelihood is None or obj.impact is None:
            return "N/A"
        return format_html(
            'L: {} / I: {}',
            obj.likelihood,
            obj.impact
        )
    likelihood_impact_display.short_description = "L/I"
    
    def risk_score_display(self, obj):
        """Display risk score with color coding."""
        if obj.likelihood is None or obj.impact is None:
            return "N/A"
        
        score = obj.risk_score
        if score >= 20:
            color = '#dc3545'  # Red
        elif score >= 15:
            color = '#dc3545'  # Red
        elif score >= 8:
            color = '#ffc107'  # Yellow
        else:
            color = '#28a745'  # Green
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            score
        )
    risk_score_display.short_description = "Score"
    
    def trend_badge(self, obj):
        """Display trend with icon and color."""
        if obj.likelihood is None or obj.impact is None:
            return "N/A"
        
        trend = obj.trend
        icons = {
            'improving': '↓',
            'stable': '→',
            'deteriorating': '↑',
            'new': '●',
        }
        colors = {
            'improving': '#28a745',
            'stable': '#6c757d',
            'deteriorating': '#dc3545',
            'new': '#007bff',
        }
        
        icon = icons.get(trend, '?')
        color = colors.get(trend, '#6c757d')
        
        return format_html(
            '<span style="color: {}; font-size: 18px; font-weight: bold;" title="{}">{}</span>',
            color,
            trend.replace('_', ' ').title(),
            icon
        )
    trend_badge.short_description = "Trend"
    
    @admin.action(description='Mark selected as current assessment')
    def mark_as_current(self, request, queryset):
        """Mark selected assessments as current."""
        count = 0
        for assessment in queryset:
            # Unmark all others for this risk
            RiskAssessment.objects.filter(
                risk=assessment.risk,
                is_current=True
            ).exclude(pk=assessment.pk).update(is_current=False)
            
            # Mark this one as current
            assessment.is_current = True
            assessment.save()
            count += 1
        
        self.message_user(request, f"{count} assessment(s) marked as current.")
    
    @admin.action(description='Generate assessment report')
    def generate_assessment_report(self, request, queryset):
        """Generate report for selected assessments."""
        # TODO: Implement report generation
        self.message_user(request, f"Report generation for {queryset.count()} assessment(s) - Feature coming soon!")

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'object_type', 'object_id')
    list_filter = ('action', 'object_type', 'created_at')
    search_fields = (
        'description',
        'object_type',
        'object_id',
        'user__username',
        'user__first_name',
        'user__last_name'
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@property
def risk_score(self):
    """Calculate risk score (likelihood × impact)."""
    if self.likelihood is not None and self.impact is not None:
        return self.likelihood * self.impact
    return 0

@property
def previous_risk_score(self):
    """Calculate previous risk score."""
    if self.previous_likelihood is not None and self.previous_impact is not None:
        return self.previous_likelihood * self.previous_impact
    return None

@property
def score_change(self):
    """Calculate change in risk score from previous assessment."""
    prev_score = self.previous_risk_score
    if prev_score is not None:
        return self.risk_score - prev_score
    return 0


# AssessmentDecision admin removed along with model removal.


# Notification admin removed along with models. See models.py and migrations.
from .models import NotificationPreference
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'enable_email_notifications', 'frequency', 'notify_time', 'expiry_date')
    search_fields = ('user__username', 'user__email')
    list_filter = ('enable_email_notifications', 'frequency')
    readonly_fields = ('created_at', 'updated_at')


# Add inline editing on the User admin so staff can edit expiry from the user page
User = get_user_model()


class NotificationPreferenceInline(admin.StackedInline):
    model = NotificationPreference
    can_delete = False
    verbose_name = 'Notification Preference'
    verbose_name_plural = 'Notification Preferences'
    fk_name = 'user'
    fields = (
        'enable_email_notifications',
        'enable_pending_assessments', 'enable_upcoming_assessments', 'enable_overdue_assessments', 'upcoming_days_assessment',
        'enable_pending_mitigations', 'enable_upcoming_mitigations', 'enable_overdue_mitigations', 'upcoming_days_mitigation',
        'notify_time', 'frequency', 'minimum_risk_level', 'expiry_date'
    )


try:
    admin.site.unregister(User)
except Exception:
    # If the User model wasn't registered (unlikely), ignore
    pass


@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    inlines = (NotificationPreferenceInline,)
