from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class RiskManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class Department(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class RiskCategory(models.Model):
    name = models.CharField(max_length=100)
    WEIGHT_CHOICES = [(i, i) for i in range(1, 11)]
    weight = models.PositiveSmallIntegerField(
        default=5,
        choices=WEIGHT_CHOICES,
        help_text="Importance weight for this category (1-10)",
    )

    def __str__(self):
        return self.name


class RiskCategoryImpact(models.Model):
    """Link a risk to additional categories with specific impact/likelihood per category."""
    risk = models.ForeignKey('Risk', on_delete=models.CASCADE, related_name='category_impacts')
    category = models.ForeignKey(RiskCategory, on_delete=models.CASCADE)
    impact = models.PositiveSmallIntegerField()
    likelihood = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('risk', 'category')
        verbose_name = 'Risk Category Impact'
        verbose_name_plural = 'Risk Category Impacts'
        ordering = ['-impact', '-likelihood', 'category__name']

    @property
    def score(self):
        return (self.impact or 0) * (self.likelihood or 0)

    @property
    def risk_rating(self):
        s = self.score
        if s <= 7:
            return 'Low'
        elif s <= 14:
            return 'Medium'
        elif s <= 19:
            return 'High'
        else:
            return 'Critical'

    @property
    def rating_color(self):
        mapping = {
            'Low': 'success',
            'Medium': 'warning',
            'High': 'danger',
            'Critical': 'danger',
        }
        return mapping.get(self.risk_rating, 'secondary')

    def __str__(self):
        return f"{self.risk} · {self.category.name} (I:{self.impact}, L:{self.likelihood}, S:{self.score})"


class RiskOwner(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.OneToOneField('Department', on_delete=models.CASCADE, related_name='risk_owner')
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='risk_owner_profile',
        help_text="Link to Django user account for login access"
    )

    def __str__(self):
        return f"{self.name} ({self.department.abbreviation})"

    def can_login(self):
        """Check if this risk owner can log into the system."""
        return self.user is not None and self.user.is_active


class KPI(models.Model):
    """KPI model for risk evaluation."""
    MEASUREMENT_PERIOD_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
    ]
    DIRECTION_CHOICES = [
        ("higher", "Higher is better"),
        ("lower", "Lower is better"),
    ]

    name = models.CharField(max_length=255, unique=True)
    unit = models.CharField(max_length=64, blank=True)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="higher")
    measurement_period = models.CharField(max_length=10, choices=MEASUREMENT_PERIOD_CHOICES, default="monthly")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "KPI"
        verbose_name_plural = "KPIs"


class Risk(models.Model):
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager
        controls: RelatedManager['Control']
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    category = models.ForeignKey(RiskCategory, on_delete=models.CASCADE)
    risk_number = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    cause = models.TextField()
    impact_description = models.TextField()
    
    # Inherent Risk Assessment (risk before controls)
    inherent_likelihood = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Inherent likelihood (1-5): Risk likelihood without controls"
    )
    inherent_impact = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Inherent impact (1-5): Risk impact without controls"
    )
    
    # Current/Residual Risk (calculated from inherent risk and controls)
    likelihood = models.PositiveSmallIntegerField()
    impact = models.PositiveSmallIntegerField()
    risk_owner = models.ForeignKey("RiskOwner", on_delete=models.SET_NULL, null=True, blank=True)

    # User tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_risks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_risks")
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Approval workflow fields
    STATUS_CHOICES = [
        ('parked', 'Parked/Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='parked')
    park_risk = models.BooleanField(default=False, help_text="Save as draft, not yet final for approval")
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_risks")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Optional KPI link
    linked_kpi = models.ForeignKey(KPI, on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_risks")

    # Managers for soft delete
    objects = RiskManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ('department', 'risk_number')
        ordering = ("department", "risk_number")

    @property
    def risk_id(self):
        dept_abbr = self.department.abbreviation.upper()
        return f"R{self.risk_number:02d}{dept_abbr}"

    @property
    def risk_score(self):
        """Calculate risk score (likelihood × impact)."""
        if self.likelihood is not None and self.impact is not None:
            return self.likelihood * self.impact
        return 0

    @property
    def risk_rating(self):
        if self.likelihood is not None and self.impact is not None:
            return self.likelihood * self.impact
        return 0
    
    @property
    def inherent_risk_score(self):
        """Calculate inherent risk score (before controls)."""
        if self.inherent_likelihood and self.inherent_impact:
            return self.inherent_likelihood * self.inherent_impact
        return 0
    
    def get_weighted_control_effectiveness(self):
        """Calculate weighted average of control effectiveness.
        
        Returns:
            float: Weighted average effectiveness (0-100), or 0 if no controls
        """
        controls = self.controls.filter(is_active=True)
        if not controls.exists():
            return 0.0
        
        total_weight = sum(c.weight for c in controls)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(c.effectiveness * c.weight for c in controls)
        return weighted_sum / total_weight
    
    def get_control_type_distribution(self):
        """Get distribution of control types and their effectiveness.
        
        Returns:
            dict: Control type breakdown with counts and average effectiveness
        """
        from django.db.models import Avg, Count
        
        controls = self.controls.filter(is_active=True)
        if not controls.exists():
            return {}
        
        distribution = controls.values('control_type').annotate(
            count=Count('id'),
            avg_effectiveness=Avg('effectiveness')
        )
        
        return {item['control_type']: item for item in distribution}
    
    def calculate_residual_risk(self):
        """Calculate residual risk after applying controls.
        
        Returns:
            dict: Contains residual_likelihood, residual_impact, residual_score, 
                  risk_reduction_pct, control_effectiveness
        """
        # If no inherent risk set, return current values
        if not self.inherent_likelihood or not self.inherent_impact:
            return {
                'residual_likelihood': self.likelihood,
                'residual_impact': self.impact,
                'residual_score': self.risk_score,
                'risk_reduction_pct': 0.0,
                'control_effectiveness': 0.0,
                'has_inherent_risk': False
            }
        
        # Get weighted control effectiveness
        control_effectiveness = self.get_weighted_control_effectiveness()
        
        if control_effectiveness == 0:
            # No controls - residual = inherent
            return {
                'residual_likelihood': self.inherent_likelihood,
                'residual_impact': self.inherent_impact,
                'residual_score': self.inherent_risk_score,
                'risk_reduction_pct': 0.0,
                'control_effectiveness': 0.0,
                'has_inherent_risk': True
            }
        
        # Apply control type-specific reductions
        control_types = self.get_control_type_distribution()
        
        # Calculate weighted reduction factors for likelihood and impact
        likelihood_reduction = 0.0
        impact_reduction = 0.0
        total_weight = sum(self.controls.filter(is_active=True).values_list('weight', flat=True))
        
        if total_weight > 0:
            for control in self.controls.filter(is_active=True):
                weight_factor = control.weight / total_weight
                effectiveness_factor = float(control.effectiveness) / 100.0
                
                # Control type reduction factors (likelihood%, impact%)
                type_factors = {
                    'preventive': (0.80, 0.20),
                    'detective': (0.30, 0.70),
                    'corrective': (0.10, 0.90),
                    'directive': (0.50, 0.50),
                }
                
                likelihood_factor, impact_factor = type_factors.get(
                    control.control_type, (0.50, 0.50)
                )
                
                likelihood_reduction += weight_factor * effectiveness_factor * likelihood_factor
                impact_reduction += weight_factor * effectiveness_factor * impact_factor
        
        # Calculate residual values
        residual_likelihood = max(1, round(
            self.inherent_likelihood * (1 - likelihood_reduction)
        ))
        residual_impact = max(1, round(
            self.inherent_impact * (1 - impact_reduction)
        ))
        residual_score = residual_likelihood * residual_impact
        
        # Calculate risk reduction percentage
        if self.inherent_risk_score > 0:
            risk_reduction_pct = (
                (self.inherent_risk_score - residual_score) / self.inherent_risk_score
            ) * 100
        else:
            risk_reduction_pct = 0.0
        
        return {
            'residual_likelihood': residual_likelihood,
            'residual_impact': residual_impact,
            'residual_score': residual_score,
            'risk_reduction_pct': round(risk_reduction_pct, 2),
            'control_effectiveness': round(control_effectiveness, 2),
            'has_inherent_risk': True,
            'likelihood_reduction': round(likelihood_reduction * 100, 2),
            'impact_reduction': round(impact_reduction * 100, 2)
        }
    
    @property
    def residual_likelihood(self):
        """Get calculated residual likelihood."""
        return self.calculate_residual_risk()['residual_likelihood']
    
    @property
    def residual_impact(self):
        """Get calculated residual impact."""
        return self.calculate_residual_risk()['residual_impact']
    
    @property
    def residual_risk_score(self):
        """Get calculated residual risk score."""
        return self.calculate_residual_risk()['residual_score']
    
    @property
    def risk_reduction_percentage(self):
        """Get risk reduction percentage from controls."""
        return self.calculate_residual_risk()['risk_reduction_pct']

    @property
    def max_impact(self):
        impacts = [self.impact or 0]
        try:
            category_impacts = getattr(self, 'category_impacts', None)
            if category_impacts is not None:
                impacts.extend([ci.impact or 0 for ci in category_impacts.all()])
        except Exception:
            pass
        return max(impacts) if impacts else 0

    @property
    def max_score(self):
        scores = [self.risk_score or 0]
        try:
            category_impacts = getattr(self, 'category_impacts', None)
            if category_impacts is not None:
                scores.extend([ci.score for ci in category_impacts.all()])
        except Exception:
            pass
        return max(scores) if scores else 0

    @property
    def all_categories(self):
        cats = []
        if self.category:
            cats.append(self.category)
        try:
            category_impacts = getattr(self, 'category_impacts', None)
            if category_impacts is not None:
                cats.extend([ci.category for ci in category_impacts.all()])
        except Exception:
            pass
        return cats

    @property
    def affected_categories_count(self):
        try:
            category_impacts = getattr(self, 'category_impacts', None)
            if category_impacts is not None:
                return category_impacts.count()
            return 0
        except Exception:
            return 0

    def get_category_impact(self, category):
        try:
            category_impacts = getattr(self, 'category_impacts', None)
            if category_impacts is not None:
                return category_impacts.filter(category=category).first()
            return None
        except Exception:
            return None

    def soft_delete(self, user=None):
        """Soft delete the risk."""
        self.is_deleted = True
        self.deleted_by = user
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_by", "deleted_at"])

    def restore(self):
        """Restore a soft-deleted risk."""
        self.is_deleted = False
        self.deleted_by = None
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_by", "deleted_at"])

    def approve(self, user=None):
        """Mark risk as approved."""
        self.status = 'approved'
        self.is_approved = True
        self.approved_by = user
        self.approved_at = timezone.now()
        self.park_risk = False
        self.rejection_reason = None
        self.save(update_fields=["status", "is_approved", "approved_by", "approved_at", "park_risk", "rejection_reason"])

    def reject(self, user=None, reason=''):
        """Reject the risk."""
        self.status = 'rejected'
        self.is_approved = False
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=["status", "is_approved", "approved_by", "approved_at", "rejection_reason"])

    def submit_for_approval(self):
        """Submit risk for approval."""
        self.status = 'pending'
        self.park_risk = False
        self.save(update_fields=["status", "park_risk"])

    def park(self):
        """Park risk as draft."""
        self.status = 'parked'
        self.park_risk = True
        self.save(update_fields=["status", "park_risk"])

    def unapprove(self):
        """Un-approve the risk."""
        self.status = 'parked'
        self.is_approved = False
        self.approved_by = None
        self.approved_at = None
        self.save(update_fields=["status", "is_approved", "approved_by", "approved_at"])

    @property
    def latest_assessment_with_indicators(self):
        """Get the latest assessment with all its indicator assessments."""
        from django.apps import apps
        RiskAssessment = apps.get_model('riskregister', 'RiskAssessment')
        IndicatorAssessment = apps.get_model('riskregister', 'IndicatorAssessment')
        
        # Prefer explicitly marked current assessment, then completed/approved, then any assessment
        latest_assessment = RiskAssessment.objects.filter(risk=self, is_current=True).order_by('-assessment_date', '-created_at').first()
        if not latest_assessment:
            latest_assessment = RiskAssessment.objects.filter(risk=self, status__in=['completed', 'approved']).order_by('-assessment_date', '-created_at').first()
        if not latest_assessment:
            latest_assessment = RiskAssessment.objects.filter(risk=self).order_by('-assessment_date', '-created_at').first()
        
        if not latest_assessment:
            return None
        
        # Get all indicator assessments linked to this risk assessment
        # Use the reverse relationship from the ManyToManyField
        indicator_assessments = IndicatorAssessment.objects.filter(
            resulting_risk_assessments=latest_assessment
        ).select_related(
            'indicator', 'indicator__preferred_kpi'
        ).order_by('indicator__preferred_kpi_name')
        
        return {
            'assessment': latest_assessment,
            'indicator_assessments': list(indicator_assessments),
            'total_indicators': indicator_assessments.count(),
            'on_target': indicator_assessments.filter(status='on_target').count(),
            'caution': indicator_assessments.filter(status='caution').count(),
            'breached': indicator_assessments.filter(status='breached').count(),
        }

    def get_all_assessments_with_indicators(self):
        """Get all assessments with their indicator assessments, newest first."""
        from django.apps import apps
        RiskAssessment = apps.get_model('riskregister', 'RiskAssessment')
        IndicatorAssessment = apps.get_model('riskregister', 'IndicatorAssessment')
        
        # Get all assessments, prioritizing completed/approved ones
        assessments = RiskAssessment.objects.filter(risk=self).order_by('-assessment_date', '-created_at')
        
        result = []
        # We'll show, for each risk assessment, the indicator assessment that was current
        # at the time of the risk assessment. Prefer indicator assessments explicitly
        # linked to the risk assessment; otherwise pick the latest assessment per
        # indicator with assessment_date <= risk assessment date.
        RiskIndicator = apps.get_model('riskregister', 'RiskIndicator')
        for assessment in assessments:
            assessment_date = getattr(assessment, 'assessment_date', None)

            # First, try any indicator assessments explicitly linked to this risk assessment
            linked_ias = IndicatorAssessment.objects.filter(resulting_risk_assessments=assessment).select_related(
                'indicator', 'indicator__preferred_kpi'
            )

            if linked_ias.exists():
                display_indicator_assessments = list(linked_ias.order_by('-assessment_date'))
            else:
                # Build a one-per-indicator snapshot as of assessment_date
                display_indicator_assessments = []
                indicators = RiskIndicator.objects.filter(risk=self)
                for indicator in indicators:
                    if assessment_date:
                        ia = IndicatorAssessment.objects.filter(
                            indicator=indicator,
                            assessment_date__lte=assessment_date
                        ).select_related('indicator', 'indicator__preferred_kpi').order_by('-assessment_date').first()
                    else:
                        ia = IndicatorAssessment.objects.filter(
                            indicator=indicator
                        ).select_related('indicator', 'indicator__preferred_kpi').order_by('-assessment_date').first()

                    if ia:
                        display_indicator_assessments.append(ia)

            # Compute counts from the snapshot list
            total_indicators = len(display_indicator_assessments)
            on_target = sum(1 for ia in display_indicator_assessments if ia.status == 'on_target')
            caution = sum(1 for ia in display_indicator_assessments if ia.status == 'caution')
            breached = sum(1 for ia in display_indicator_assessments if ia.status == 'breached')

            result.append({
                'assessment': assessment,
                'indicator_assessments': display_indicator_assessments,
                'total_indicators': total_indicators,
                'on_target': on_target,
                'caution': caution,
                'breached': breached,
            })
        
        return result

    def save(self, *args, **kwargs):
        # Auto-assign risk number if not set
        if not self.risk_number:
            last_risk = Risk.all_objects.filter(department=self.department).order_by('-risk_number').first()
            self.risk_number = 1 if not last_risk or not last_risk.risk_number else last_risk.risk_number + 1
        
        # On initial creation, if inherent risk is set but assessed risk is not, 
        # automatically set assessed risk to equal residual risk
        if not self.pk and self.inherent_likelihood and self.inherent_impact:
            # This is a new risk being created
            if not self.likelihood or not self.impact:
                # Calculate residual risk
                residual_data = self.calculate_residual_risk()
                self.likelihood = residual_data['residual_likelihood']
                self.impact = residual_data['residual_impact']
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.risk_id + ": " + self.title


class RiskIndicator(models.Model):
    """Risk evaluation indicator settings - Multiple indicators per risk.

    This version stores operators as readable keys (e.g. 'gt','gte') and provides
    helper methods to show human friendly labels and symbols. Comparison logic
    maps the operator key to the actual comparison.
    """

    APPETITE_LEVEL_CHOICES = [
        ("none", "None / Not set"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("very_high", "Very High"),
    ]
    AGGREGATION_METHOD_CHOICES = [
        ("average", "Average"),
        ("sum", "Sum"),
        ("max", "Max"),
    ]

    # Human-friendly operator keys + labels
    OP_GT = "gt"
    OP_GTE = "gte"
    OP_LT = "lt"
    OP_LTE = "lte"
    OP_EQ = "eq"

    # Choice tuples: (value, label shown in forms/admin)
    OPERATOR_CHOICES = [
        (OP_GT, "Greater than (>)"),
        (OP_GTE, "Greater than or equal (>=)"),
        (OP_LT, "Less than (<)"),
        (OP_LTE, "Less than or equal (<=)"),
        (OP_EQ, "Equal to (==)"),
    ]

    # Mapping from key to symbol for display
    OPERATOR_SYMBOL = {
        OP_GT: ">",
        OP_GTE: ">=",
        OP_LT: "<",
        OP_LTE: "<=",
        OP_EQ: "==",
    }

    # Mapping from key to a callable that compares Decimals (v op t)
    OPERATOR_FUNC = {
        OP_GT: lambda v, t: v > t,
        OP_GTE: lambda v, t: v >= t,
        OP_LT: lambda v, t: v < t,
        OP_LTE: lambda v, t: v <= t,
        OP_EQ: lambda v, t: v == t,
    }

    # Direction hint (used for interpretation & UI)
    DIRECTION_INCREASE = "increase"
    DIRECTION_DECREASE = "decrease"
    DIRECTION_CHOICES = [
        (DIRECTION_INCREASE, "Higher is worse"),
        (DIRECTION_DECREASE, "Lower is worse"),
    ]

    risk = models.ForeignKey(
        'Risk', on_delete=models.CASCADE, related_name="indicators"
    )
    
    # Link to parent Risk Assessment (one assessment -> many indicators)
    risk_assessment = models.ForeignKey(
        'RiskAssessment',
        on_delete=models.CASCADE,
        related_name="linked_indicators",
        null=True,
        blank=True,
        help_text="The risk assessment this indicator belongs to"
    )
    
    # Scheduled assessment date for this indicator
    scheduled_assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Scheduled date for assessing this indicator (must be <= parent assessment date)"
    )
    
    # Status tracking for indicator completion
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Assessment'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of this indicator assessment"
    )
    
    # Individual indicator result and rationale
    indicator_result = models.TextField(
        blank=True,
        help_text="Result/outcome of this specific indicator assessment"
    )
    
    indicator_rationale = models.TextField(
        blank=True,
        help_text="Rationale/comments for this indicator's assessment result"
    )

    appetite_level = models.CharField(
        max_length=16, choices=APPETITE_LEVEL_CHOICES, default="medium"
    )
    appetite_tolerance_pct = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("10.00"))

    preferred_kpi = models.ForeignKey(
        KPI, on_delete=models.SET_NULL, null=True, blank=True, related_name="as_indicator"
    )
    preferred_kpi_name = models.CharField(max_length=255, blank=True)
    aggregation_method = models.CharField(
        max_length=10, choices=AGGREGATION_METHOD_CHOICES, default="average"
    )

    measurement_period = models.CharField(max_length=16, default="monthly")

    unit = models.CharField(max_length=50, blank=True)
    data_source = models.CharField(max_length=255, blank=True, help_text="Where to collect the measurement from")

    # Trigger and breach thresholds with readable operator keys
    trigger_threshold = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    trigger_operator = models.CharField(max_length=4, choices=OPERATOR_CHOICES, default=OP_GTE)

    breach_threshold = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    breach_operator = models.CharField(max_length=4, choices=OPERATOR_CHOICES, default=OP_GT)

    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default=DIRECTION_INCREASE)

    escalation_actions = models.JSONField(blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["risk", "created_at"]),
        ]

    def __str__(self):
        name = self.preferred_kpi_name or getattr(self.preferred_kpi, "name", None) or f"indicator#{self.pk}"
        return f"{self.risk} · {name} [{self.appetite_level}]"

    #
    # Readable operator helpers
    #
    def _operator_symbol(self, operator_key: str) -> str:
        """Return the operator symbol (e.g. '>=') for a stored operator key."""
        return self.OPERATOR_SYMBOL.get(operator_key, "?")

    def _operator_label(self, operator_key: str) -> str:
        """Return the human-friendly label for the operator (taken from choices)."""
        for key, label in self.OPERATOR_CHOICES:
            if key == operator_key:
                return label
        return str(operator_key)

    @property
    def trigger_operator_symbol(self) -> str:
        return self._operator_symbol(self.trigger_operator)

    @property
    def breach_operator_symbol(self) -> str:
        return self._operator_symbol(self.breach_operator)

    @property
    def trigger_operator_label(self) -> str:
        return self._operator_label(self.trigger_operator)

    @property
    def breach_operator_label(self) -> str:
        return self._operator_label(self.breach_operator)

    #
    # Comparison & evaluation
    #
    @staticmethod
    def _to_decimal(value):
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            return None

    def _compare_with_key(self, value, operator_key, threshold) -> bool:
        """Compare value against threshold using the operator_key mapping."""
        v = self._to_decimal(value)
        t = self._to_decimal(threshold)
        if v is None or t is None:
            return False
        func = self.OPERATOR_FUNC.get(operator_key)
        if not func:
            return False
        try:
            return func(v, t)
        except Exception:
            return False

    def evaluate(self, value):
        """Evaluate a measurement value against trigger and breach thresholds.

        Returns:
          - "unknown" if no thresholds or value invalid,
          - "breached" if the breach condition is met,
          - "caution" if the trigger condition is met (but not breach),
          - "ok" otherwise.
        """
        if not self.active:
            return "inactive"

        # Validate numeric value
        if self._to_decimal(value) is None:
            return "unknown"

        # breach first
        if self.breach_threshold is not None and self.breach_operator:
            if self._compare_with_key(value, self.breach_operator, self.breach_threshold):
                return "breached"

        # then trigger
        if self.trigger_threshold is not None and self.trigger_operator:
            if self._compare_with_key(value, self.trigger_operator, self.trigger_threshold):
                return "caution"

        return "ok"

    def human_readable_rule(self) -> str:
        """Return a concise human readable rule summary, e.g.
           'Caution if >= 45; Breach if > 60 (unit: minutes)'"""
        parts = []
        if self.trigger_threshold is not None:
            parts.append(f"Caution if {self.trigger_operator_symbol} {self.trigger_threshold}")
        if self.breach_threshold is not None:
            parts.append(f"Breach if {self.breach_operator_symbol} {self.breach_threshold}")
        if parts:
            unit = f" (unit: {self.unit})" if self.unit else ""
            return "; ".join(parts) + unit
        return "No thresholds configured"
    
    def generate_assessment_schedules(self, start_date=None, num_periods=12):
        """
        Generate periodic measurement schedules for this indicator.
        This ensures assessments are aligned with the measurement period.
        
        Args:
            start_date: Date to start generating from (default: today)
            num_periods: Number of periods to generate (default: 12)
        
        Returns:
            List of created PeriodicMeasurementSchedule instances
        """
        from datetime import date
        from .models import PeriodicMeasurementSchedule
        
        if start_date is None:
            start_date = date.today()
        
        return PeriodicMeasurementSchedule.generate_schedule_for_indicator(
            indicator=self,
            start_date=start_date,
            num_periods=num_periods
        )
    
    @property
    def latest_assessment(self):
        """Get the most recent assessment for this indicator"""
        try:
            # Import here to avoid circular dependency
            from django.apps import apps
            IndicatorAssessment = apps.get_model('riskregister', 'IndicatorAssessment')
            return IndicatorAssessment.objects.filter(indicator=self, is_current=True).first()
        except Exception:
            return None
    
    @property
    def assessment_trend(self):
        """Get assessment trend over last 6 periods"""
        try:
            # Import here to avoid issues with forward references
            from django.apps import apps
            IndicatorAssessment = apps.get_model('riskregister', 'IndicatorAssessment')
            recent = list(IndicatorAssessment.objects.filter(indicator=self).order_by('-assessment_date')[:6])
            if len(recent) < 2:
                return 'insufficient_data'
            
            # Count improving vs deteriorating using getattr to safely access trend
            improving = sum(1 for a in recent if getattr(a, 'trend', None) == 'improving')
            deteriorating = sum(1 for a in recent if getattr(a, 'trend', None) == 'deteriorating')
            
            if improving > deteriorating:
                return 'improving'
            elif deteriorating > improving:
                return 'deteriorating'
            else:
                return 'stable'
        except Exception:
            return 'unknown'
    
    @property
    def name(self):
        """Get the indicator name from preferred_kpi_name or preferred_kpi"""
        return self.preferred_kpi_name or (self.preferred_kpi.name if self.preferred_kpi else f"Indicator #{self.pk}")
    
    def validate_scheduled_date(self):
        """Validate that scheduled_assessment_date is not after parent assessment date"""
        from django.core.exceptions import ValidationError
        
        if self.risk_assessment and self.scheduled_assessment_date:
            if self.scheduled_assessment_date > self.risk_assessment.assessment_date:
                raise ValidationError({
                    'scheduled_assessment_date': f'Scheduled date ({self.scheduled_assessment_date}) cannot be after parent assessment date ({self.risk_assessment.assessment_date})'
                })
    
    def mark_completed(self, result='', rationale=''):
        """Mark this indicator as completed"""
        self.status = 'completed'
        if result:
            self.indicator_result = result
        if rationale:
            self.indicator_rationale = rationale
        self.save()
    
    def clean(self):
        """Model validation"""
        super().clean()
        self.validate_scheduled_date()
    
    def save(self, *args, **kwargs):
        # Run validation before save
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)


class IndicatorMeasurement(models.Model):
    """Time-series measurement for a RiskIndicator. Useful for trends, dashboards and alerting."""

    indicator = models.ForeignKey(RiskIndicator, related_name="measurements", on_delete=models.CASCADE)
    measured_at = models.DateTimeField(default=timezone.now, db_index=True)
    value = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-measured_at",)
        indexes = [
            models.Index(fields=["indicator", "measured_at"]),
        ]

    def __str__(self):
        return f"{self.indicator} @ {self.measured_at:%Y-%m-%d %H:%M} = {self.value}"

    @property
    def status(self):
        if self.value is None:
            return "unknown"
        return self.indicator.evaluate(self.value)


class IndicatorAssessment(models.Model):
    """
    Comprehensive assessment of a risk indicator with full audit trail.
    Aligned with measurement schedules and provides trend analysis.
    """
    
    STATUS_CHOICES = [
        ('on_target', 'On Target'),
        ('caution', 'Caution'),
        ('breached', 'Breached'),
        ('not_measured', 'Not Measured'),
    ]
    
    TREND_CHOICES = [
        ('improving', 'Improving'),
        ('stable', 'Stable'),
        ('deteriorating', 'Deteriorating'),
        ('new', 'New Assessment'),
    ]
    
    indicator = models.ForeignKey(
        RiskIndicator, 
        on_delete=models.CASCADE, 
        related_name="assessments"
    )
    
    # Link to the measurement schedule this assessment fulfills
    schedule = models.ForeignKey(
        'PeriodicMeasurementSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="indicator_assessments"
    )
    
    # Link to the actual measurement record
    measurement = models.OneToOneField(
        IndicatorMeasurement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment"
    )
    
    # Assessment details
    assessment_date = models.DateField(db_index=True)
    assessment_period_start = models.DateField(
        help_text="Start date of the period being assessed"
    )
    assessment_period_end = models.DateField(
        help_text="End date of the period being assessed"
    )
    
    # Value and status
    measured_value = models.DecimalField(
        max_digits=18, 
        decimal_places=6,
        null=True,
        blank=True,
        help_text="The actual measured value"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='not_measured'
    )
    
    # For financial indicators
    is_financial = models.BooleanField(default=False)
    currency_code = models.CharField(
        max_length=10,
        blank=True,
        default='USD',
        help_text="Currency code (USD, ZWL, EUR, etc.)"
    )
    
    # Comparison with previous
    previous_value = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    variance = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Difference from previous value"
    )
    
    variance_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage change from previous"
    )
    
    trend = models.CharField(
        max_length=20,
        choices=TREND_CHOICES,
        default='new'
    )
    
    # Detailed assessment information
    assessment_notes = models.TextField(
        blank=True,
        help_text="Detailed notes about this assessment"
    )
    
    analysis = models.TextField(
        blank=True,
        help_text="Analysis of the results and any variances"
    )
    
    corrective_actions = models.TextField(
        blank=True,
        help_text="Recommended or taken corrective actions"
    )
    
    evidence_documents = models.FileField(
        upload_to='indicator_assessments/',
        blank=True,
        null=True,
        help_text="Supporting documentation"
    )
    
    # Tracking
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="indicator_assessments"
    )
    
    is_current = models.BooleanField(
        default=True,
        help_text="Is this the most recent assessment?"
    )
    
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    # NEW: Whether this assessment triggered a risk reassessment
    triggered_risk_assessment = models.BooleanField(
        default=False,
        help_text="Whether this assessment triggered a full risk reassessment"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assessment_date', '-created_at']
        indexes = [
            models.Index(fields=['indicator', 'assessment_date']),
            models.Index(fields=['status', 'assessment_date']),
            models.Index(fields=['is_current', 'indicator']),
        ]
        unique_together = [['indicator', 'assessment_date']]
    
    def __str__(self):
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return f"{self.indicator} - {self.assessment_date:%Y-%m-%d} - {status_display}"
    
    def save(self, *args, **kwargs):
        # Calculate variance if previous value exists
        if self.previous_value is not None and self.measured_value is not None:
            self.variance = self.measured_value - self.previous_value
            
            # Calculate percentage change
            if self.previous_value != 0:
                self.variance_percentage = (self.variance / self.previous_value) * 100
            else:
                self.variance_percentage = None
        
        # Determine status based on indicator thresholds
        if self.measured_value is not None:
            self.status = self.indicator.evaluate(self.measured_value)
        
        # Determine trend
        if self.previous_value is None:
            self.trend = 'new'
        elif self.variance is not None:
            if abs(self.variance) < (self.previous_value * Decimal('0.05')):  # Less than 5% change
                self.trend = 'stable'
            elif self.variance > 0:
                # Positive change - determine if improving or deteriorating based on direction
                if self.indicator.direction == 'decrease':  # Lower is better
                    self.trend = 'deteriorating'
                else:  # Higher is better
                    self.trend = 'improving'
            else:  # Negative change
                if self.indicator.direction == 'decrease':  # Lower is better
                    self.trend = 'improving'
                else:  # Higher is better
                    self.trend = 'deteriorating'
        
        super().save(*args, **kwargs)
    
    @property
    def formatted_value(self):
        """Return formatted value with currency symbol if financial"""
        if self.measured_value is None:
            return "Not measured"
        
        if self.is_financial:
            currency_symbols = {
                'USD': '$',
                'ZWL': 'ZWL$',
                'EUR': '€',
                'GBP': '£',
                'ZAR': 'R',
            }
            symbol = currency_symbols.get(self.currency_code, self.currency_code)
            return f"{symbol}{self.measured_value:,.2f}"
        else:
            return f"{self.measured_value:.2f}"
    
    @property
    def formatted_variance(self):
        """Return formatted variance with + or - sign"""
        if self.variance is None:
            return "N/A"
        
        sign = "+" if self.variance >= 0 else ""
        if self.is_financial:
            currency_symbols = {
                'USD': '$',
                'ZWL': 'ZWL$',
                'EUR': '€',
                'GBP': '£',
                'ZAR': 'R',
            }
            symbol = currency_symbols.get(self.currency_code, self.currency_code)
            return f"{sign}{symbol}{self.variance:,.2f}"
        else:
            return f"{sign}{self.variance:.2f}"
    
    @property
    def days_since_assessment(self):
        """Calculate days since this assessment"""
        from datetime import date
        return (date.today() - self.assessment_date).days
    
    @classmethod
    def create_from_schedule(cls, schedule, measured_value, notes="", assessed_by=None):
        """
        Create an assessment from a measurement schedule.
        This ensures alignment between schedules and assessments.
        """
        # Get previous assessment for comparison
        previous = cls.objects.filter(
            indicator=schedule.indicator,
            is_current=True
        ).first()
        
        # Mark all previous assessments as not current
        cls.objects.filter(indicator=schedule.indicator).update(is_current=False)
        
        # Create measurement record
        measurement = IndicatorMeasurement.objects.create(
            indicator=schedule.indicator,
            measured_at=timezone.now(),
            value=measured_value,
            notes=notes
        )
        
        # Determine if financial indicator
        is_financial = False
        currency_code = 'USD'
        if schedule.indicator.unit and any(curr in schedule.indicator.unit.upper() for curr in ['USD', 'ZWL', 'EUR', 'GBP', '$']):
            is_financial = True
            if 'ZWL' in schedule.indicator.unit.upper():
                currency_code = 'ZWL'
            elif 'EUR' in schedule.indicator.unit.upper() or '€' in schedule.indicator.unit:
                currency_code = 'EUR'
            elif 'GBP' in schedule.indicator.unit.upper() or '£' in schedule.indicator.unit:
                currency_code = 'GBP'
        
        # Check if assessment already exists for this date
        assessment_date = schedule.scheduled_date
        existing_assessment = cls.objects.filter(
            indicator=schedule.indicator,
            assessment_date=assessment_date
        ).first()
        
        if existing_assessment:
            # Update existing assessment
            existing_assessment.schedule = schedule
            existing_assessment.measurement = measurement
            existing_assessment.assessment_period_start = schedule.start_date
            existing_assessment.assessment_period_end = schedule.end_date
            existing_assessment.measured_value = measured_value
            existing_assessment.previous_value = previous.measured_value if previous else None
            existing_assessment.is_financial = is_financial
            existing_assessment.currency_code = currency_code
            existing_assessment.assessment_notes = notes
            existing_assessment.assessed_by = assessed_by
            existing_assessment.is_current = True
            existing_assessment.save()
            assessment = existing_assessment
        else:
            # Create new assessment
            assessment = cls.objects.create(
                indicator=schedule.indicator,
                schedule=schedule,
                measurement=measurement,
                assessment_date=assessment_date,
                assessment_period_start=schedule.start_date,
                assessment_period_end=schedule.end_date,
                measured_value=measured_value,
                previous_value=previous.measured_value if previous else None,
                is_financial=is_financial,
                currency_code=currency_code,
                assessment_notes=notes,
                assessed_by=assessed_by,
                is_current=True
            )
        
        # Mark schedule as completed
        schedule.mark_completed(measurement, user=assessed_by)
        
        return assessment


# AssessmentDecision removed per request: functionality and audit records
# Note: Database records should be purged using the provided SQL script
# scripts/delete_assessment_decisions.sql or via a managed migration prior to
# migrating the code that removes the model from the schema.

class ActivityLog(models.Model):
    """Generic activity log for user actions across the system."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    context = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['object_type', 'object_id']),
        ]

    def __str__(self):
        user_display = self.user.get_full_name() if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {user_display} - {self.action}"


class Control(models.Model):
    """Internal controls for risk management with weighted effectiveness."""
    
    CONTROL_TYPE_CHOICES = [
        ('preventive', 'Preventive - Prevents risk occurrence (80% likelihood, 20% impact)'),
        ('detective', 'Detective - Detects risk after occurrence (30% likelihood, 70% impact)'),
        ('corrective', 'Corrective - Corrects after occurrence (10% likelihood, 90% impact)'),
        ('directive', 'Directive - Directs behavior (50% likelihood, 50% impact)'),
    ]
    
    if TYPE_CHECKING:
        def get_control_type_display(self) -> str: ...
    
    WEIGHT_CHOICES = [
        (1, '1 - Minimal importance'),
        (2, '2 - Very low importance'),
        (3, '3 - Low importance'),
        (4, '4 - Below average importance'),
        (5, '5 - Average importance'),
        (6, '6 - Above average importance'),
        (7, '7 - Moderately high importance'),
        (8, '8 - High importance'),
        (9, '9 - Very high importance'),
        (10, '10 - Critical importance'),
    ]
    
    risk = models.ForeignKey(
        Risk,
        on_delete=models.CASCADE,
        related_name='controls'
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Name or brief description of the control"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of how the control works"
    )
    
    control_type = models.CharField(
        max_length=20,
        choices=CONTROL_TYPE_CHOICES,
        help_text="Type of control determines how it reduces risk"
    )
    
    effectiveness = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Control effectiveness percentage (0-100%)"
    )
    
    weight = models.PositiveSmallIntegerField(
        default=5,
        choices=WEIGHT_CHOICES,
        help_text="Importance/weight of this control (1-10 scale)"
    )
    
    # Custom weight criteria (optional, user can define what weight means)
    weight_rationale = models.TextField(
        blank=True,
        help_text="Explanation for why this weight was assigned"
    )
    
    # Control owner/responsible person
    control_owner = models.ForeignKey(
        "RiskOwner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_controls'
    )
    
    # Frequency of control execution
    frequency = models.CharField(
        max_length=50,
        blank=True,
        help_text="How often the control is executed (e.g., daily, monthly, continuous)"
    )
    
    # Testing and validation
    last_tested_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the control was last tested"
    )
    
    test_results = models.TextField(
        blank=True,
        help_text="Results from the most recent test"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this control is currently active"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_controls'
    )
    
    class Meta:
        ordering = ['-weight', 'control_type', 'name']
        verbose_name = 'Control'
        verbose_name_plural = 'Controls'
    
    def __str__(self):
        return f"{self.name} ({self.get_control_type_display()}) - {self.effectiveness}% effective"
    
    @property
    def weighted_effectiveness(self):
        """Calculate the weighted contribution of this control."""
        return (float(self.effectiveness) * self.weight) / 100.0
    
    @property
    def control_type_display_short(self):
        """Get short display name for control type."""
        return self.control_type.capitalize()
    
    def get_reduction_factors(self):
        """Get the likelihood and impact reduction factors for this control type."""
        factors = {
            'preventive': {'likelihood': 80, 'impact': 20},
            'detective': {'likelihood': 30, 'impact': 70},
            'corrective': {'likelihood': 10, 'impact': 90},
            'directive': {'likelihood': 50, 'impact': 50},
        }
        return factors.get(self.control_type, {'likelihood': 50, 'impact': 50})
    
    def clean(self):
        """Validate control data."""
        from django.core.exceptions import ValidationError
        
        if self.effectiveness < 0 or self.effectiveness > 100:
            raise ValidationError({
                'effectiveness': 'Effectiveness must be between 0 and 100'
            })
        
        if self.weight < 1 or self.weight > 10:
            raise ValidationError({
                'weight': 'Weight must be between 1 and 10'
            })


class Mitigation(models.Model):
    STRATEGY_CHOICES = [
        ('accept', 'Accept'),
        ('transfer', 'Transfer'),
        ('reduce', 'Reduce'),
        ('avoid', 'Avoid'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('postponed', 'Postponed'),
        ('partially_implemented', 'Partially Implemented'),
        ('not_achieved', 'Not Achieved'),
        ('cancelled', 'Cancelled'),
    ]

    risk = models.ForeignKey(Risk, related_name='mitigations', on_delete=models.CASCADE)
    strategy = models.CharField(max_length=30, choices=STRATEGY_CHOICES)
    action = models.TextField()
    evidence = models.FileField(upload_to='mitigation_evidence/', blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    responsible_person = models.ForeignKey("RiskOwner", on_delete=models.SET_NULL, null=True, blank=True)
    
    # Enhanced tracking fields
    completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="Percentage of mitigation completed (0-100)"
    )
    postponement_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this mitigation has been postponed"
    )
    last_postponed_date = models.DateField(blank=True, null=True)
    original_due_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.strategy.capitalize()} - {self.risk.risk_id}"
    
    @property
    def is_overdue(self):
        """Check if mitigation is overdue"""
        if self.due_date and self.status not in ['complete', 'cancelled']:
            from datetime import date
            return self.due_date < date.today()
        return False
    
    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if self.is_overdue and self.due_date:
            from datetime import date
            return (date.today() - self.due_date).days
        return 0
    
    def log_progress(self, user, action_type, notes='', completion_percentage=None, evidence=None):
        """Helper method to log mitigation progress"""
        return MitigationProgressLog.objects.create(
            mitigation=self,
            user=user,
            action_type=action_type,
            notes=notes,
            completion_percentage=completion_percentage or self.completion_percentage,
            status_at_time=self.status,
            evidence=evidence
        )

    def record_progress_update(
        self,
        user=None,
        action_type='status_change',
        notes='',
        previous_status=None,
        previous_completion_percentage=None,
        previous_due_date=None,
        completion_percentage=None,
        due_date_at_time=None,
        postponement_reason='',
        new_target_date=None,
        failure_reason='',
        lessons_learned='',
        evidence=None,
    ):
        """Create a detailed MitigationProgressLog entry summarising an update.

        This centralises progress logging so views can call a single method
        rather than constructing the log object in-line.
        """
        return MitigationProgressLog.objects.create(
            mitigation=self,
            user=user,
            action_type=action_type,
            notes=notes,
            status_at_time=self.status,
            previous_status=previous_status or '',
            completion_percentage=(completion_percentage if completion_percentage is not None else self.completion_percentage),
            previous_completion_percentage=(previous_completion_percentage if previous_completion_percentage is not None else 0),
            due_date_at_time=due_date_at_time,
            previous_due_date=previous_due_date,
            postponement_reason=postponement_reason,
            new_target_date=new_target_date,
            failure_reason=failure_reason,
            lessons_learned=lessons_learned,
            evidence=evidence,
        )


class MitigationProgressLog(models.Model):
    """Tracks detailed progression trail for each mitigation action"""
    
    ACTION_TYPE_CHOICES = [
        ('created', 'Mitigation Created'),
        ('status_change', 'Status Changed'),
        ('postponed', 'Postponed'),
        ('partial_completion', 'Partial Completion'),
        ('due_date_extended', 'Due Date Extended'),
        ('responsibility_changed', 'Responsibility Changed'),
        ('evidence_added', 'Evidence Added'),
        ('progress_update', 'Progress Update'),
        ('completion_failed', 'Completion Failed'),
        ('cancelled', 'Cancelled'),
        ('resumed', 'Resumed'),
    ]
    
    mitigation = models.ForeignKey(
        Mitigation, 
        on_delete=models.CASCADE, 
        related_name='progress_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mitigation_progress_logs'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE_CHOICES)
    notes = models.TextField(
        blank=True,
        help_text="Detailed notes about this action"
    )
    
    # Status tracking
    status_at_time = models.CharField(
        max_length=30,
        blank=True,
        help_text="Mitigation status at the time of this log entry"
    )
    previous_status = models.CharField(
        max_length=30,
        blank=True,
        help_text="Previous status before this change"
    )
    
    # Completion tracking
    completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="Completion percentage at time of log (0-100)"
    )
    previous_completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="Previous completion percentage"
    )
    
    # Date tracking
    due_date_at_time = models.DateField(blank=True, null=True)
    previous_due_date = models.DateField(blank=True, null=True)
    
    # Evidence
    evidence = models.FileField(
        upload_to='mitigation_progress_evidence/', 
        blank=True, 
        null=True
    )
    
    # Postponement details
    postponement_reason = models.TextField(
        blank=True,
        help_text="Reason for postponement (if applicable)"
    )
    new_target_date = models.DateField(
        blank=True, 
        null=True,
        help_text="New target date after postponement"
    )
    
    # Failure details
    failure_reason = models.TextField(
        blank=True,
        help_text="Reason for not achieving mitigation (if applicable)"
    )
    lessons_learned = models.TextField(
        blank=True,
        help_text="Lessons learned from partial/failed implementation"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mitigation', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
        ]
        verbose_name = 'Mitigation Progress Log'
        verbose_name_plural = 'Mitigation Progress Logs'
    
    def __str__(self):
        user_display = self.user.get_full_name() if self.user else 'System'
        action_type_display = dict(self.ACTION_TYPE_CHOICES).get(self.action_type, self.action_type)
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.mitigation.action[:50]} - {action_type_display}"
    
    @property
    def completion_change(self):
        """Calculate change in completion percentage"""
        return self.completion_percentage - self.previous_completion_percentage
    
    @property
    def days_postponed(self):
        """Calculate days postponed if applicable"""
        if self.previous_due_date and self.new_target_date:
            return (self.new_target_date - self.previous_due_date).days
        return 0


class PeriodicMeasurementSchedule(models.Model):
    """Tracks scheduled periodic measurements for risk indicators based on their measurement period."""
    
    PERIOD_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annually", "Annually"),
    ]
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
        ("skipped", "Skipped"),
    ]
    
    indicator = models.ForeignKey(
        RiskIndicator, 
        on_delete=models.CASCADE, 
        related_name="scheduled_measurements"
    )
    
    # Period configuration
    period_type = models.CharField(
        max_length=20, 
        choices=PERIOD_CHOICES,
        help_text="How frequently this measurement should be taken"
    )
    
    # Scheduling dates
    scheduled_date = models.DateField(
        db_index=True,
        help_text="The date when this measurement is due"
    )
    start_date = models.DateField(
        help_text="Start of the measurement period"
    )
    end_date = models.DateField(
        help_text="End of the measurement period"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="pending"
    )
    
    # Linked measurement (when completed)
    completed_measurement = models.OneToOneField(
        IndicatorMeasurement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="schedule"
    )
    
    # Completion tracking
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_measurements"
    )
    
    # Reminders and notifications
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and comments
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-scheduled_date", "indicator"]
        indexes = [
            models.Index(fields=["indicator", "scheduled_date"]),
            models.Index(fields=["status", "scheduled_date"]),
            models.Index(fields=["scheduled_date"]),
        ]
        unique_together = [["indicator", "scheduled_date"]]
    
    def __str__(self):
        return f"{self.indicator} - {self.period_type} - Due: {self.scheduled_date}"
    
    @property
    def is_overdue(self):
        """Check if this scheduled measurement is overdue."""
        from datetime import date
        if self.scheduled_date is None:
            return False
        return self.status == "pending" and self.scheduled_date < date.today()

    @property
    def days_until_due(self):
        """Calculate days until measurement is due (negative if overdue)."""
        from datetime import date
        if self.scheduled_date is None:
            return 0
        delta = self.scheduled_date - date.today()
        return delta.days
    
    def mark_completed(self, measurement, user=None):
        """Mark this schedule as completed with a linked measurement."""
        self.status = "completed"
        self.completed_measurement = measurement
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save(update_fields=["status", "completed_measurement", "completed_at", "completed_by", "updated_at"])
    
    def mark_skipped(self, reason=""):
        """Mark this scheduled measurement as skipped."""
        self.status = "skipped"
        if reason:
            self.notes = f"{self.notes}\nSkipped: {reason}".strip()
        self.save(update_fields=["status", "notes", "updated_at"])
    
    def update_status(self):
        """Update status based on current date and completion."""
        if self.status == "completed" or self.status == "skipped":
            return
        
        if self.is_overdue:
            self.status = "overdue"
            self.save(update_fields=["status", "updated_at"])
    
    def send_reminder(self):
        """Send reminder notification for pending measurement."""
        if not self.reminder_sent and self.status in ["pending", "overdue"]:
            # TODO: Implement actual reminder logic (email, notification, etc.)
            self.reminder_sent = True
            self.reminder_sent_at = timezone.now()
            self.save(update_fields=["reminder_sent", "reminder_sent_at", "updated_at"])
            return True
        return False
    
    @classmethod
    def generate_schedule_for_indicator(cls, indicator, start_date, num_periods=12):
        """Generate scheduled measurements for an indicator based on its period.
        
        Args:
            indicator: RiskIndicator instance
            start_date: Date to start generating schedules from
            num_periods: Number of periods to generate (default 12)
        
        Returns:
            List of created PeriodicMeasurementSchedule instances
        """
        
        
        schedules = []
        current_date = start_date
        period_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": relativedelta(months=1),
            "quarterly": relativedelta(months=3),
            "annually": relativedelta(years=1),
        }
        
        period_type = indicator.measurement_period
        if period_type not in period_map:
            period_type = "monthly"  # default
        
        for i in range(num_periods):
            # Calculate period boundaries
            period_start = current_date
            
            if period_type == "daily":
                period_end = period_start
                scheduled = period_start
            elif period_type == "weekly":
                period_end = period_start + timedelta(days=6)
                scheduled = period_end
            elif period_type == "monthly":
                period_end = period_start + relativedelta(months=1) - timedelta(days=1)
                scheduled = period_end
            elif period_type == "quarterly":
                period_end = period_start + relativedelta(months=3) - timedelta(days=1)
                scheduled = period_end
            elif period_type == "annually":
                period_end = period_start + relativedelta(years=1) - timedelta(days=1)
                scheduled = period_end
            else:
                period_end = period_start + relativedelta(months=1) - timedelta(days=1)
                scheduled = period_end
            
            # Create schedule if it doesn't exist
            schedule, created = cls.objects.get_or_create(
                indicator=indicator,
                scheduled_date=scheduled,
                defaults={
                    "period_type": period_type,
                    "start_date": period_start,
                    "end_date": period_end,
                    "status": "pending",
                }
            )
            
            if created:
                schedules.append(schedule)
            
            # Move to next period
            if period_type == "daily":
                current_date += timedelta(days=1)
            elif period_type == "weekly":
                current_date += timedelta(weeks=1)
            elif period_type == "monthly":
                current_date += relativedelta(months=1)
            elif period_type == "quarterly":
                current_date += relativedelta(months=3)
            elif period_type == "annually":
                current_date += relativedelta(years=1)
        
        return schedules
    
    @classmethod
    def get_assessments_due_soon(cls, days=15):
        """
        Get indicator assessments (schedules) due within the specified number of days.
        Used for generating reminders and alerts.
        
        Args:
            days: Number of days to look ahead (default: 15)
        
        Returns:
            QuerySet of PeriodicMeasurementSchedule instances
        """
        from datetime import date, timedelta
        today = date.today()
        future_date = today + timedelta(days=days)
        
        return cls.objects.filter(
            status='pending',
            scheduled_date__gte=today,
            scheduled_date__lte=future_date,
            reminder_sent=False
        ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    @classmethod
    def get_overdue_assessments(cls):
        """
        Get all overdue assessments that haven't been completed.
        
        Returns:
            QuerySet of overdue PeriodicMeasurementSchedule instances
        """
        from datetime import date
        today = date.today()
        
        return cls.objects.filter(
            status='pending',
            scheduled_date__lt=today
        ).select_related('indicator', 'indicator__risk').order_by('scheduled_date')
    
    @classmethod
    def send_reminders_batch(cls, days_ahead=7):
        """
        Send reminders for all assessments due within the specified days.
        
        Args:
            days_ahead: Days to look ahead for sending reminders (default: 7)
        
        Returns:
            List of schedules that were sent reminders
        """
        schedules = cls.get_assessments_due_soon(days=days_ahead)
        reminded = []
        
        for schedule in schedules:
            if schedule.send_reminder():
                reminded.append(schedule)
        
        return reminded


class RiskAssessment(models.Model):
    """Track risk assessments over time to show risk movement and trends."""
    
    ASSESSMENT_TYPE_CHOICES = [
        ('initial', 'Initial Assessment'),
        ('periodic', 'Periodic Review'),
        ('incident', 'Post-Incident Assessment'),
        ('mitigation', 'Post-Mitigation Assessment'),
        ('ad_hoc', 'Ad-Hoc Assessment'),
    ]
    
    TREND_CHOICES = [
        ('improving', 'Improving (Risk Decreasing)'),
        ('stable', 'Stable (No Change)'),
        ('deteriorating', 'Deteriorating (Risk Increasing)'),
        ('new', 'New Assessment'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('pending_indicators', 'Pending Indicators'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ]
    
    risk = models.ForeignKey(
        Risk,
        on_delete=models.CASCADE,
        related_name='assessments'  # One risk -> many assessments
    )
    
    # Assessment details
    assessment_date = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Date when this assessment was conducted"
    )
    assessment_type = models.CharField(
        max_length=20,
        choices=ASSESSMENT_TYPE_CHOICES,
        default='periodic'
    )
    
    # Assessment status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the assessment"
    )
    
    # Overall assessment result and rationale
    overall_result = models.TextField(
        blank=True,
        help_text="Overall assessment result/conclusion"
    )
    overall_rationale = models.TextField(
        blank=True,
        help_text="Overall rationale explaining the final risk evaluation"
    )
    assessment_type = models.CharField(
        max_length=20,
        choices=ASSESSMENT_TYPE_CHOICES,
        default='periodic'
    )
    
    # Risk scores at time of assessment
    likelihood = models.PositiveSmallIntegerField(
        help_text="Likelihood score (1-5)"
    )
    impact = models.PositiveSmallIntegerField(
        help_text="Impact score (1-5)"
    )
    
    # Assessment context
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risk_assessments'
    )
    
    # Change tracking from previous assessment
    previous_likelihood = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Likelihood from previous assessment"
    )
    previous_impact = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Impact from previous assessment"
    )
    
    # Justification and notes
    rationale = models.TextField(
        blank=True,
        help_text="Explanation for the likelihood and impact scores"
    )
    changes_since_last = models.TextField(
        blank=True,
        help_text="What has changed since the last assessment"
    )
    evidence = models.TextField(
        blank=True,
        help_text="Evidence supporting this assessment"
    )
    
    # Recommendations
    recommendations = models.TextField(
        blank=True,
        help_text="Recommended actions based on this assessment"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_current = models.BooleanField(
        default=True,
        help_text="Is this the most recent assessment for this risk?"
    )
    
    # NEW: Link to source indicator assessments
    source_indicator_assessments = models.ManyToManyField(
        'IndicatorAssessment',
        related_name='resulting_risk_assessments',
        blank=True,
        help_text="Indicator assessments that informed this risk assessment"
    )
    
    # NEW: Aggregated indicator status
    aggregate_status = models.CharField(
        max_length=20,
        choices=[
            ('on_target', 'On Target'),
            ('caution', 'Caution'),
            ('breached', 'Breached'),
            ('mixed', 'Mixed Results'),
            ('none', 'No Indicators'),
        ],
        null=True,
        blank=True,
        help_text="Overall status aggregated from indicator assessments"
    )
    
    # NEW: Counts from indicator assessments
    indicators_on_target = models.IntegerField(
        default=0,
        help_text="Number of indicators on target"
    )
    indicators_in_caution = models.IntegerField(
        default=0,
        help_text="Number of indicators in caution zone"
    )
    indicators_breached = models.IntegerField(
        default=0,
        help_text="Number of indicators breached"
    )
    
    # NEW: Executive summary for reporting
    executive_summary = models.TextField(
        blank=True,
        help_text="High-level summary for executive reports"
    )
    
    # NEW: Key findings as JSON
    key_findings = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured key findings from indicator assessments"
    )
    
    class Meta:
        ordering = ['-assessment_date', '-created_at']
        indexes = [
            models.Index(fields=['risk', 'assessment_date']),
            models.Index(fields=['assessment_date']),
            models.Index(fields=['is_current']),
        ]
        verbose_name = 'Risk Assessment'
        verbose_name_plural = 'Risk Assessments'
    
    def __str__(self):
        return f"{self.risk.risk_id} - Assessment on {self.assessment_date}"
    
    @property
    def risk_score(self):
        """Calculate risk score (likelihood × impact)."""
        if self.likelihood is not None and self.impact is not None:
            return self.likelihood * self.impact
        return 0
    
    @property
    def previous_risk_score(self):
        """Calculate previous risk score."""
        if self.previous_likelihood and self.previous_impact:
            return self.previous_likelihood * self.previous_impact
        return None
    
    @property
    def score_change(self):
        """Calculate change in risk score from previous assessment."""
        if self.previous_risk_score:
            return self.risk_score - self.previous_risk_score
        return 0
    
    @property
    def score_change_percentage(self):
        """Calculate percentage change in risk score."""
        if self.previous_risk_score and self.previous_risk_score > 0:
            return ((self.risk_score - self.previous_risk_score) / self.previous_risk_score) * 100
        return 0
    
    @property
    def trend(self):
        """Determine risk trend based on score changes."""
        if self.previous_risk_score is None:
            return 'new'
        
        change = self.score_change
        if change < 0:
            return 'improving'
        elif change > 0:
            return 'deteriorating'
        else:
            return 'stable'
    
    @property
    def risk_level(self):
        """Get risk level based on score."""
        score = self.risk_score
        if score >= 20:
            return 'critical'
        elif score >= 15:
            return 'high'
        elif score >= 8:
            return 'medium'
        else:
            return 'low'
    
    @property
    def previous_risk_level(self):
        """Get previous risk level."""
        if self.previous_risk_score:
            score = self.previous_risk_score
            if score >= 20:
                return 'critical'
            elif score >= 15:
                return 'high'
            elif score >= 8:
                return 'medium'
            else:
                return 'low'
        return None
    
    @property
    def rating(self):
        """Alias for risk_level to support templates"""
        return self.risk_level
    
    def get_rating_class(self):
        """Get Bootstrap CSS class for risk rating"""
        level = self.risk_level
        mapping = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success',
        }
        return mapping.get(level, 'secondary')
    
    def get_rating_display(self):
        """Get display text for risk rating"""
        return self.risk_level.upper()
    
    def aggregate_from_indicators(self, period_start, period_end):
        """Aggregate indicator assessments from a time period"""
        from django.db.models import Count
        
        indicator_assessments = IndicatorAssessment.objects.filter(
            indicator__risk=self.risk,
            assessment_date__range=[period_start, period_end]
        )
        
        if not indicator_assessments.exists():
            self.aggregate_status = 'none'
            self.save()
            return
        
        # Count by status
        self.indicators_on_target = indicator_assessments.filter(status='on_target').count()
        self.indicators_in_caution = indicator_assessments.filter(status='caution').count()
        self.indicators_breached = indicator_assessments.filter(status='breached').count()
        
        # Determine aggregate status
        if self.indicators_breached > 0:
            self.aggregate_status = 'breached'
        elif self.indicators_in_caution > 0:
            self.aggregate_status = 'caution'
        elif self.indicators_on_target > 0:
            self.aggregate_status = 'on_target'
        else:
            self.aggregate_status = 'mixed'
        
        # Link source assessments
        self.source_indicator_assessments.set(indicator_assessments)
        
        # Generate key findings
        findings = []
        for assessment in indicator_assessments.filter(status__in=['breached', 'caution']):
            findings.append({
                'indicator': assessment.indicator.preferred_kpi_name,
                'status': assessment.status,
                'value': str(assessment.measured_value),
                'date': assessment.assessment_date.isoformat(),
            })
        self.key_findings = findings
        
        self.save()
    
    def get_indicator_assessments_summary(self):
        """Get summary of all indicator assessments linked to this risk assessment."""
        from django.apps import apps
        IndicatorAssessment = apps.get_model('riskregister', 'IndicatorAssessment')
        
        indicator_assessments = self.source_indicator_assessments.select_related(
            'indicator', 'indicator__preferred_kpi'
        ).order_by('indicator__preferred_kpi_name', '-assessment_date')
        
        summary = []
        for ind_assessment in indicator_assessments:
            summary.append({
                'id': ind_assessment.id,
                'indicator_name': ind_assessment.indicator.preferred_kpi_name or ind_assessment.indicator.name,
                'measured_value': ind_assessment.measured_value,
                'status': ind_assessment.status,
                'status_display': ind_assessment.get_status_display(),
                'assessment_date': ind_assessment.assessment_date,
                'assessment_period': f"{ind_assessment.assessment_period_start} to {ind_assessment.assessment_period_end}",
                'notes': ind_assessment.notes,
                'assessor': ind_assessment.assessor.get_full_name() if ind_assessment.assessor else 'N/A',
                'trend': ind_assessment.trend,
                'variance_percentage': ind_assessment.variance_percentage,
            })
        
        return summary
    
    @property
    def level_changed(self):
        """Check if risk level changed from previous assessment."""
        if self.previous_risk_level:
            return self.risk_level != self.previous_risk_level
        return False
    
    @property
    def matrix_position(self):
        """Return the position on the risk matrix as a dict."""
        return {
            'likelihood': self.likelihood,
            'impact': self.impact,
            'score': self.risk_score,
            'level': self.risk_level
        }
    
    @property
    def previous_matrix_position(self):
        """Return previous position on the risk matrix."""
        if self.previous_likelihood and self.previous_impact:
            return {
                'likelihood': self.previous_likelihood,
                'impact': self.previous_impact,
                'score': self.previous_risk_score,
                'level': self.previous_risk_level
            }
        return None
    
    def can_be_completed(self):
        """Check if all linked indicators are completed"""
        # Only check if this assessment is already saved (has a pk)
        if not self.pk:
            return True, "New assessment - indicator validation will occur after save"
        
        linked = RiskIndicator.objects.filter(risk_id=self.risk.pk, risk_assessment_id=self.pk)
        if not linked.exists():
            return False, "No indicators linked to this assessment"
        
        incomplete = linked.exclude(status='completed')
        if incomplete.exists():
            return False, f"{incomplete.count()} indicator(s) still incomplete: {', '.join([i.name for i in incomplete[:5]])}"
        
        return True, "All indicators are completed"
    
    def validate_indicator_schedules(self):
        """Validate that all indicator scheduled dates are before or equal to assessment date"""
        # Only validate if this assessment is already saved (has a pk)
        if not self.pk:
            return True, "New assessment - schedule validation will occur after save"
        
        invalid_indicators = RiskIndicator.objects.filter(
            risk_id=self.risk.pk, 
            risk_assessment_id=self.pk,
            scheduled_assessment_date__gt=self.assessment_date
        )
        
        if invalid_indicators.exists():
            invalid_names = ', '.join([i.name for i in invalid_indicators[:5]])
            return False, f"These indicators have scheduled dates after the assessment date: {invalid_names}"
        
        return True, "All indicator schedules are valid"
    
    def mark_completed(self, user=None):
        """Attempt to mark assessment as completed with validation"""
        from django.core.exceptions import ValidationError
        
        # Check if all indicators are completed
        can_complete, message = self.can_be_completed()
        if not can_complete:
            raise ValidationError(message)
        
        # Validate schedules
        valid_schedules, schedule_message = self.validate_indicator_schedules()
        if not valid_schedules:
            raise ValidationError(schedule_message)
        
        # Mark as completed
        self.status = 'completed'
        if user:
            self.assessor = user
        self.save()
        
        return True
    
    def get_indicator_breakdown(self):
        """Get detailed breakdown of all linked indicators with their results"""
        # Only get indicators if this assessment is saved
        if not self.pk:
            return []
        
        indicators = RiskIndicator.objects.filter(risk_id=self.risk.pk, risk_assessment_id=self.pk).select_related('preferred_kpi')
        
        breakdown = []
        for indicator in indicators:
            breakdown.append({
                'id': indicator.pk,
                'name': indicator.name,
                'status': dict(RiskIndicator.STATUS_CHOICES).get(indicator.status, indicator.status),
                'scheduled_date': indicator.scheduled_assessment_date,
                'result': indicator.indicator_result,
                'rationale': indicator.indicator_rationale,
                'is_completed': indicator.status == 'completed',
            })
        
        return breakdown
    
    def clean(self):
        """Model validation"""
        from django.core.exceptions import ValidationError
        
        super().clean()
        
        # Validate indicator schedules on save
        if self.pk:  # Only for existing instances
            valid, message = self.validate_indicator_schedules()
            if not valid:
                raise ValidationError({'assessment_date': message})
        
        # Prevent completion if indicators are incomplete
        if self.status == 'completed':
            can_complete, message = self.can_be_completed()
            if not can_complete:
                raise ValidationError({'status': message})
    
    @property
    def movement_vector(self):
        """Calculate movement vector from previous assessment."""
        if self.previous_likelihood and self.previous_impact:
            return {
                'likelihood_change': self.likelihood - self.previous_likelihood,
                'impact_change': self.impact - self.previous_impact,
                'score_change': self.score_change,
                'score_change_pct': round(self.score_change_percentage, 1),
                'direction': self.trend,
                'level_changed': self.level_changed,
                'from_level': self.previous_risk_level,
                'to_level': self.risk_level
            }
        return None
    
    def get_previous_assessment(self):
        """Get the assessment that was current before this one."""
        return RiskAssessment.objects.filter(
            risk=self.risk,
            assessment_date__lt=self.assessment_date
        ).order_by('-assessment_date', '-created_at').first()
    
    def save(self, *args, **kwargs):
        """Override save to automatically populate previous values and manage is_current flag."""
        # Run full_clean before save (unless explicitly skipped)
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        
        is_new = self.pk is None
        
        if is_new:
            # Get the most recent assessment for this risk
            previous = RiskAssessment.objects.filter(
                risk=self.risk
            ).order_by('-assessment_date', '-created_at').first()
            
            if previous:
                # Populate previous values from the last assessment
                self.previous_likelihood = previous.likelihood
                self.previous_impact = previous.impact
            else:
                # This is the first assessment - no previous values
                self.previous_likelihood = None
                self.previous_impact = None
        
        # If this is marked as current, mark all others as not current
        if self.is_current:
            RiskAssessment.objects.filter(
                risk=self.risk
            ).exclude(pk=self.pk).update(is_current=False)
        
        super().save(*args, **kwargs)
        
        # Update the parent Risk model with current assessment values
        if self.is_current:
            self.risk.likelihood = self.likelihood
            self.risk.impact = self.impact
            self.risk.save(update_fields=['likelihood', 'impact'])
    
    def compare_with_assessment(self, other_assessment):
        """Compare this assessment with another specific assessment.
        
        Args:
            other_assessment: Another RiskAssessment instance to compare with
            
        Returns:
            dict: Comparison data including changes and trends
        """
        if not other_assessment or other_assessment.risk != self.risk:
            return None
        
        likelihood_change = self.likelihood - other_assessment.likelihood
        impact_change = self.impact - other_assessment.impact
        score_change = self.risk_score - other_assessment.risk_score
        
        # Determine trend
        if score_change > 0:
            trend = 'deteriorating'
        elif score_change < 0:
            trend = 'improving'
        else:
            trend = 'stable'
        
        # Calculate percentage change
        if other_assessment.risk_score > 0:
            score_change_pct = (score_change / other_assessment.risk_score) * 100
        else:
            score_change_pct = 0
        
        # Check if risk level changed
        level_changed = self.risk_level != other_assessment.risk_level
        
        return {
            'other_date': other_assessment.assessment_date,
            'other_type': other_assessment.get_assessment_type_display(),
            'likelihood_change': likelihood_change,
            'impact_change': impact_change,
            'score_change': score_change,
            'score_change_pct': round(score_change_pct, 1),
            'trend': trend,
            'level_changed': level_changed,
            'from_level': other_assessment.risk_level,
            'to_level': self.risk_level,
            'from_score': other_assessment.risk_score,
            'to_score': self.risk_score,
            'time_difference_days': (self.assessment_date - other_assessment.assessment_date).days
        }
    
    def get_movement_description(self):
        """Get human-readable description of risk movement from previous assessment."""
        if not self.movement_vector:
            return "Initial assessment - no previous data"
        
        vector = self.movement_vector
        likelihood_change = vector['likelihood_change']
        impact_change = vector['impact_change']
        score_change = vector['score_change']
        score_change_pct = vector['score_change_pct']
        
        parts = []
        
        # Describe likelihood change
        if likelihood_change > 0:
            parts.append(f"Likelihood increased by {likelihood_change} point(s)")
        elif likelihood_change < 0:
            parts.append(f"Likelihood decreased by {abs(likelihood_change)} point(s)")
        
        # Describe impact change
        if impact_change > 0:
            parts.append(f"Impact increased by {impact_change} point(s)")
        elif impact_change < 0:
            parts.append(f"Impact decreased by {abs(impact_change)} point(s)")
        
        if not parts:
            return "No change from previous assessment"
        
        description = "; ".join(parts)
        
        # Add overall score change
        if score_change > 0:
            description += f" (Overall risk score increased by {score_change} points, +{score_change_pct}%)"
        elif score_change < 0:
            description += f" (Overall risk score decreased by {abs(score_change)} points, {score_change_pct}%)"
        
        # Add level change if applicable
        if vector['level_changed']:
            description += f" - Risk level changed from {vector['from_level'].upper()} to {vector['to_level'].upper()}"
        
        return description
    
    def get_comparison_summary(self):
        """Get a comprehensive comparison summary with previous assessment."""
        previous = self.get_previous_assessment()
        if not previous:
            return {
                'has_previous': False,
                'is_first': True,
                'message': 'This is the first assessment for this risk'
            }
        
        comparison = self.compare_with_assessment(previous)
        
        return {
            'has_previous': True,
            'is_first': False,
            'previous_assessment': previous,
            'comparison': comparison,
            'movement': self.movement_vector,
            'description': self.get_movement_description()
        }
    
    @classmethod
    def get_assessment_history(cls, risk, limit=None):
        """Get assessment history for a risk."""
        assessments = cls.objects.filter(risk_id=risk.pk).order_by('-assessment_date', '-created_at')
        if limit:
            return list(assessments[:limit])
        return assessments
    
    @classmethod
    def get_trend_data(cls, risk):
        """Get trend data for charting risk movement over time."""
        assessments = cls.objects.filter(risk_id=risk.pk).order_by('assessment_date')
        
        data = []
        previous_score = None
        
        for assessment in assessments:
            score = assessment.risk_score
            
            # Calculate change from previous
            if previous_score is not None:
                change = score - previous_score
                change_pct = (change / previous_score * 100) if previous_score > 0 else 0
            else:
                change = 0
                change_pct = 0
            
            data.append({
                'date': assessment.assessment_date.isoformat(),
                'date_display': assessment.assessment_date.strftime('%b %d, %Y'),
                'likelihood': assessment.likelihood,
                'impact': assessment.impact,
                'score': score,
                'level': assessment.risk_level,
                'type': assessment.assessment_type,
                'type_display': dict(cls.ASSESSMENT_TYPE_CHOICES).get(assessment.assessment_type, assessment.assessment_type),
                'change': change,
                'change_pct': round(change_pct, 1),
                'assessor': assessment.assessor.get_full_name() if assessment.assessor else 'Unknown'
            })
            
            previous_score = score
        
        return data
    
    @classmethod
    def get_comparison_between_dates(cls, risk, start_date, end_date):
        """Compare assessments between two dates."""
        start_assessment = cls.objects.filter(
            risk=risk,
            assessment_date__lte=start_date
        ).order_by('-assessment_date').first()
        
        end_assessment = cls.objects.filter(
            risk=risk,
            assessment_date__lte=end_date
        ).order_by('-assessment_date').first()
        
        if not start_assessment or not end_assessment:
            return None
        
        return end_assessment.compare_with_assessment(start_assessment)


# Notification models removed per user request.
# If you need to reintroduce notifications, re-create the model classes
# `NotificationRule`, `NotificationPreference`, and `Notification` here
# Reintroduce a simplified per-user NotificationPreference model
from django.conf import settings


class NotificationPreference(models.Model):
    """Per-user notification preferences for assessments and mitigations.

    These preferences control which types of email reminders a user receives
    and basic scheduling options. This intentionally keeps a small surface
    so it is easy to extend later (e.g. channels, complex rules).
    """
    FREQUENCY_CHOICES = (
        ('immediate', 'Immediate'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    enable_email_notifications = models.BooleanField(default=True)

    # Assessment toggles
    enable_pending_assessments = models.BooleanField(default=True)
    enable_upcoming_assessments = models.BooleanField(default=True)
    enable_overdue_assessments = models.BooleanField(default=True)
    upcoming_days_assessment = models.PositiveIntegerField(default=2, help_text='How many days ahead to consider an assessment "upcoming"')

    # Mitigation toggles
    enable_pending_mitigations = models.BooleanField(default=True)
    enable_upcoming_mitigations = models.BooleanField(default=True)
    enable_overdue_mitigations = models.BooleanField(default=True)
    upcoming_days_mitigation = models.PositiveIntegerField(default=2, help_text='How many days ahead to consider a mitigation "upcoming"')

    # When to deliver (time of day). If null, send immediately when scheduler runs.
    notify_time = models.TimeField(null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')

    # Optional: explicit expiry datetime for the user account. When set,
    # a periodic job will deactivate the related `user` after this date/time.
    expiry_date = models.DateTimeField(null=True, blank=True, help_text='If set, user will be deactivated after this date/time')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Admin-only threshold: minimum risk level to notify about
    RISK_LEVEL_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    minimum_risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='low', help_text='Admin: minimum risk level to trigger notifications')

    def __str__(self):
        return f"NotificationPreference({self.user})"

# and add a migration to create them. They were intentionally removed.


class AssessmentScheduleConfig(models.Model):
    """Configuration for automatic assessment scheduling per risk"""
    
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ]
    
    risk = models.OneToOneField(
        Risk, 
        on_delete=models.CASCADE, 
        related_name='schedule_config'
    )
    
    # Risk-level assessment frequency
    risk_assessment_frequency = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES,
        default='quarterly',
        help_text="How often to conduct full risk assessments"
    )
    
    # Minimum indicator assessments required before risk assessment
    min_indicator_assessments = models.IntegerField(
        default=1,
        help_text="Minimum number of indicator assessments required"
    )
    
    # Auto-trigger risk assessment when X indicators breach
    auto_trigger_on_breached = models.IntegerField(
        default=2,
        help_text="Auto-trigger risk assessment when this many indicators breach"
    )
    
    # Generate schedules X months in advance
    schedule_advance_months = models.IntegerField(
        default=12,
        help_text="Generate schedules this many months in advance"
    )
    
    # Last schedule generation date
    last_generated = models.DateField(
        null=True, 
        blank=True,
        help_text="Last date schedules were generated"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether automatic scheduling is active for this risk"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Assessment Schedule Configuration'
        verbose_name_plural = 'Assessment Schedule Configurations'
    
    def __str__(self):
        return f"Schedule Config for {self.risk.risk_id}"
    
    def generate_schedules(self):
        """Generate assessment schedules for all indicators and risk"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        end_date = today + relativedelta(months=self.schedule_advance_months)
        
        # Generate indicator schedules
        for indicator in RiskIndicator.objects.filter(risk_id=self.risk.pk, active=True):
            self._generate_indicator_schedules(indicator, today, end_date)
        
        # Generate risk assessment schedules (placeholder for future enhancement)
        self._generate_risk_assessment_schedules(today, end_date)
        
        self.last_generated = today
        self.save()
    
    def _generate_indicator_schedules(self, indicator, start_date, end_date):
        """Generate schedules for a specific indicator"""
        from dateutil.relativedelta import relativedelta
        
        # Map measurement period to relativedelta
        period_map = {
            'daily': relativedelta(days=1),
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi_annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
        }
        
        period_delta = period_map.get(indicator.measurement_period, relativedelta(months=1))
        
        current_date = start_date
        while current_date <= end_date:
            # Check if schedule already exists
            existing = PeriodicMeasurementSchedule.objects.filter(
                indicator=indicator,
                scheduled_date=current_date
            ).exists()
            
            if not existing:
                # Create schedule
                period_start = current_date - period_delta
                PeriodicMeasurementSchedule.objects.create(
                    indicator=indicator,
                    scheduled_date=current_date,
                    start_date=period_start,
                    end_date=current_date,
                    status='pending'
                )
            
            current_date += period_delta
    
    def _generate_risk_assessment_schedules(self, start_date, end_date):
        """Generate risk-level assessment schedules"""
        from dateutil.relativedelta import relativedelta
        
        frequency_map = {
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi_annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
        }
        
        delta = frequency_map.get(self.risk_assessment_frequency, relativedelta(months=3))
        
        # This creates a marker for when risk assessments should be done
        # Actual risk assessments are triggered by indicator assessment completion
        current_date = start_date
        while current_date <= end_date:
            # Future: Create RiskAssessmentSchedule entries
            current_date += delta


# Signal to update assessed risk when controls are added/updated
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='riskregister.Control')
def update_assessed_risk_after_control_save(sender, instance, created, **kwargs):
    """
    When a control is created or updated, automatically update the risk's 
    assessed likelihood and impact to match the calculated residual risk.
    """
    risk = instance.risk
    
    # Only update if inherent risk is set
    if risk.inherent_likelihood and risk.inherent_impact:
        residual_data = risk.calculate_residual_risk()
        
        # Update the assessed/current risk to match residual risk
        risk.likelihood = residual_data['residual_likelihood']
        risk.impact = residual_data['residual_impact']
        risk.save(update_fields=['likelihood', 'impact'])
