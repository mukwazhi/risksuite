# Risk Assessment Framework Refactoring - Implementation Guide

**Date:** January 7, 2026  
**Migration:** 0021_riskassessment_overall_rationale_and_more.py

---

## Overview

This refactoring enforces a strict hierarchical relationship between Risk Assessments and Risk Indicators with comprehensive validation logic to ensure data integrity and proper workflow.

---

## Key Changes

### 1. Data Model Relationship

**NEW STRUCTURE:**
- **RiskAssessment** → Many **RiskIndicators** (one-to-many relationship)
- Each RiskIndicator must belong to a single RiskAssessment
- RiskIndicator now has `risk_assessment` ForeignKey field

**Field Added to RiskIndicator:**
```python
risk_assessment = models.ForeignKey(
    'RiskAssessment',
    on_delete=models.CASCADE,
    related_name="linked_indicators",
    null=True,
    blank=True,
    help_text="The risk assessment this indicator belongs to"
)
```

**Access Pattern:**
```python
# Get all indicators for an assessment
indicators = assessment.linked_indicators.all()

# Get parent assessment from indicator
parent_assessment = indicator.risk_assessment
```

---

### 2. Assessment Status and Completion Logic

**NEW: RiskAssessment Status Field**
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('pending_indicators', 'Pending Indicators'),
    ('completed', 'Completed'),
    ('approved', 'Approved'),
]

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default='draft'
)
```

**NEW: RiskIndicator Status Field**
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('pending', 'Pending Assessment'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
]

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default='draft'
)
```

**Completion Validation:**
- RiskAssessment can ONLY be marked as "completed" when ALL linked indicators have status='completed'
- Automatic validation prevents premature completion
- View displays clear warnings about incomplete indicators

---

### 3. Overall Result and Rationale Fields

**NEW: RiskAssessment Fields**
```python
overall_result = models.TextField(
    blank=True,
    help_text="Overall assessment result/conclusion"
)

overall_rationale = models.TextField(
    blank=True,
    help_text="Overall rationale explaining the final risk evaluation"
)
```

**NEW: RiskIndicator Fields**
```python
indicator_result = models.TextField(
    blank=True,
    help_text="Result/outcome of this specific indicator assessment"
)

indicator_rationale = models.TextField(
    blank=True,
    help_text="Rationale/comments for this indicator's assessment result"
)
```

**Display Logic:**
- Assessment detail view prominently displays overall_result and overall_rationale
- Indicator breakdown table shows each indicator's result and rationale
- Complete audit trail from indicator level to assessment level

---

### 4. Scheduling Constraint

**NEW: RiskIndicator Field**
```python
scheduled_assessment_date = models.DateField(
    null=True,
    blank=True,
    help_text="Scheduled date for assessing this indicator (must be <= parent assessment date)"
)
```

**Validation Rule:**
```
indicator.scheduled_assessment_date <= risk_assessment.assessment_date
```

**Enforcement:**
- Validated in `RiskIndicator.clean()` method
- Validated in `RiskAssessment.clean()` method
- Raises ValidationError if constraint violated
- Prevents save if validation fails (unless `skip_validation=True`)

**Error Messages:**
- "Scheduled date (YYYY-MM-DD) cannot be after parent assessment date (YYYY-MM-DD)"
- "These indicators have scheduled dates after the assessment date: [indicator names]"

---

## New Model Methods

### RiskAssessment Methods

**1. `can_be_completed()`**
```python
can_complete, message = assessment.can_be_completed()
# Returns: (True, "All indicators are completed") or (False, "X indicator(s) still incomplete...")
```

**2. `validate_indicator_schedules()`**
```python
valid, message = assessment.validate_indicator_schedules()
# Returns: (True, "All indicator schedules are valid") or (False, "These indicators have scheduled dates after...")
```

**3. `mark_completed(user=None)`**
```python
try:
    assessment.mark_completed(user=request.user)
    # Success: status changed to 'completed'
except ValidationError as e:
    # Handle error: incomplete indicators or invalid schedules
```

**4. `get_indicator_breakdown()`**
```python
breakdown = assessment.get_indicator_breakdown()
# Returns list of dicts with indicator details:
# [{
#     'id': 1,
#     'name': 'Indicator Name',
#     'status': 'Completed',
#     'scheduled_date': date(2026, 1, 15),
#     'result': 'Result text',
#     'rationale': 'Rationale text',
#     'is_completed': True
# }, ...]
```

**5. `clean()` - Automatic Validation**
- Validates all indicator schedules
- Prevents completion if indicators incomplete
- Called automatically on save()

### RiskIndicator Methods

**1. `validate_scheduled_date()`**
```python
indicator.validate_scheduled_date()
# Raises ValidationError if scheduled_date > parent assessment_date
```

**2. `mark_completed(result='', rationale='')`**
```python
indicator.mark_completed(
    result='Indicator shows positive trend',
    rationale='Based on last 6 months data...'
)
# Sets status='completed' and saves result/rationale
```

**3. `name` Property**
```python
name = indicator.name
# Returns: preferred_kpi_name or preferred_kpi.name or "Indicator #ID"
```

**4. `clean()` - Automatic Validation**
- Validates scheduled_assessment_date constraint
- Called automatically on save()

---

## View Updates

### risk_assessment_detail View

**New Context Variables:**
```python
context = {
    # ... existing ...
    'linked_indicators': linked_indicators,  # QuerySet of RiskIndicator
    'indicator_breakdown': assessment.get_indicator_breakdown(),  # List of dicts
    'can_complete': can_complete,  # Boolean
    'completion_message': completion_message,  # String
}
```

---

## Template Updates

### risk_assessment_detail.html

**1. Overall Result and Rationale Section**
- Displays prominently after risk metrics
- Uses alert-info styling for overall_result
- Shows overall_rationale in dedicated section
- Only displays if fields have content

**2. Assessment Status Display**
- Shows current status with color-coded badge
- green = completed, yellow = pending_indicators, gray = draft/in_progress

**3. Linked Indicators Breakdown Table**
- Shows all indicators linked to assessment
- Columns: Name, Status, Scheduled Date, Result, Rationale
- Highlights incomplete indicators (yellow row background)
- Displays status badges with appropriate colors
- Truncates long result/rationale text
- Shows "Pending" or "-" for empty fields

**4. Completion Status Alert**
- Red warning alert if assessment cannot be completed
- Green success alert if all indicators are completed
- Shows specific message about what's preventing completion

---

## Migration Steps

### Step 1: Create Migration
```bash
python manage.py makemigrations riskregister
```

**Expected Output:**
```
Migrations for 'riskregister':
  riskregister\migrations\0021_riskassessment_overall_rationale_and_more.py
    + Add field overall_rationale to riskassessment
    + Add field overall_result to riskassessment
    + Add field status to riskassessment
    + Add field indicator_rationale to riskindicator
    + Add field indicator_result to riskindicator
    + Add field risk_assessment to riskindicator
    + Add field scheduled_assessment_date to riskindicator
    + Add field status to riskindicator
```

### Step 2: Apply Migration
```bash
python manage.py migrate riskregister
```

**Post-Migration State:**
- All new fields added with default values
- Existing records remain intact
- risk_assessment field is nullable (can be null for now)
- status fields default to 'draft'

### Step 3: Data Migration (Optional)
If you need to link existing indicators to assessments:

```python
from riskregister.models import Risk, RiskAssessment, RiskIndicator

# For each risk, link its indicators to its most recent assessment
for risk in Risk.objects.all():
    latest_assessment = risk.assessments.order_by('-assessment_date').first()
    if latest_assessment:
        # Link all indicators to latest assessment
        RiskIndicator.objects.filter(risk=risk).update(
            risk_assessment=latest_assessment
        )
```

### Step 4: Update Existing Workflows

**Before Completing Assessments:**
```python
# Check if can be completed
can_complete, message = assessment.can_be_completed()
if can_complete:
    assessment.mark_completed(user=request.user)
else:
    # Show error to user
    messages.error(request, message)
```

**When Creating/Updating Indicators:**
```python
try:
    indicator.scheduled_assessment_date = some_date
    indicator.save()
except ValidationError as e:
    # Handle scheduling conflict
    messages.error(request, str(e))
```

---

## Usage Examples

### Example 1: Create Assessment with Indicators

```python
from riskregister.models import Risk, RiskAssessment, RiskIndicator
from datetime import date, timedelta

# Create assessment
risk = Risk.objects.get(pk=1)
assessment = RiskAssessment.objects.create(
    risk=risk,
    assessment_date=date.today() + timedelta(days=30),
    assessment_type='periodic',
    likelihood=3,
    impact=4,
    status='draft',
    overall_rationale='Q1 2026 Periodic Review'
)

# Create linked indicators
indicator1 = RiskIndicator.objects.create(
    risk=risk,
    risk_assessment=assessment,
    preferred_kpi_name='Customer Satisfaction Score',
    scheduled_assessment_date=date.today() + timedelta(days=15),
    status='pending',
    unit='%'
)

indicator2 = RiskIndicator.objects.create(
    risk=risk,
    risk_assessment=assessment,
    preferred_kpi_name='System Downtime Hours',
    scheduled_assessment_date=date.today() + timedelta(days=20),
    status='pending',
    unit='hours'
)

# Try to complete (will fail - indicators not completed)
try:
    assessment.mark_completed()
except ValidationError as e:
    print(e)  # "2 indicator(s) still incomplete..."
```

### Example 2: Complete Indicators and Assessment

```python
# Complete first indicator
indicator1.mark_completed(
    result='Score improved to 87%',
    rationale='Customer feedback shows 15% improvement over last quarter'
)

# Complete second indicator
indicator2.mark_completed(
    result='Downtime reduced to 2 hours',
    rationale='Infrastructure upgrades reduced incidents by 60%'
)

# Now assessment can be completed
can_complete, message = assessment.can_be_completed()
print(can_complete)  # True

# Complete the assessment
assessment.overall_result = 'Risk level decreasing - positive trend across all indicators'
assessment.overall_rationale = '''
Both key indicators show significant improvement:
- Customer satisfaction increased 15%
- System downtime reduced by 60%
Recommend maintaining current controls and monitoring trends.
'''
assessment.mark_completed(user=request.user)

print(assessment.status)  # 'completed'
```

### Example 3: Validate Scheduling Constraints

```python
# This will FAIL - indicator scheduled after assessment
assessment = RiskAssessment.objects.create(
    risk=risk,
    assessment_date=date(2026, 1, 31),  # Assessment on Jan 31
    # ...
)

try:
    indicator = RiskIndicator.objects.create(
        risk=risk,
        risk_assessment=assessment,
        scheduled_assessment_date=date(2026, 2, 15),  # Scheduled in February!
        # ...
    )
except ValidationError as e:
    print(e)  # "Scheduled date (2026-02-15) cannot be after parent assessment date (2026-01-31)"

# This will SUCCEED - indicator scheduled before assessment
indicator = RiskIndicator.objects.create(
    risk=risk,
    risk_assessment=assessment,
    scheduled_assessment_date=date(2026, 1, 20),  # Before Jan 31
    # ...
)
```

---

## API Reference

### RiskAssessment API

| Method/Property | Returns | Description |
|----------------|---------|-------------|
| `can_be_completed()` | `(bool, str)` | Check if all indicators completed |
| `validate_indicator_schedules()` | `(bool, str)` | Validate schedule constraints |
| `mark_completed(user)` | `bool` | Mark as completed with validation |
| `get_indicator_breakdown()` | `list[dict]` | Get detailed indicator data |
| `linked_indicators` | `QuerySet` | Related indicators (reverse FK) |
| `status` | `str` | Current status |
| `overall_result` | `str` | Overall conclusion |
| `overall_rationale` | `str` | Overall explanation |

### RiskIndicator API

| Method/Property | Returns | Description |
|----------------|---------|-------------|
| `validate_scheduled_date()` | `None` | Validate schedule constraint |
| `mark_completed(result, rationale)` | `None` | Mark as completed |
| `name` | `str` | Indicator display name |
| `risk_assessment` | `RiskAssessment` | Parent assessment |
| `scheduled_assessment_date` | `date` | Scheduled date |
| `status` | `str` | Current status |
| `indicator_result` | `str` | Assessment result |
| `indicator_rationale` | `str` | Assessment rationale |

---

## Best Practices

### 1. Always Validate Before Completing
```python
# GOOD
can_complete, msg = assessment.can_be_completed()
if can_complete:
    assessment.mark_completed(user)
else:
    handle_error(msg)

# BAD
assessment.status = 'completed'  # May fail validation
assessment.save()
```

### 2. Set Scheduled Dates Early
```python
# Set scheduled_assessment_date when creating indicator
indicator = RiskIndicator.objects.create(
    risk_assessment=assessment,
    scheduled_assessment_date=date.today() + timedelta(days=7),
    # ...
)
```

### 3. Complete Indicators Before Assessment
```python
# Workflow: Indicators → Assessment
for indicator in assessment.linked_indicators.all():
    # Assess each indicator
    indicator.mark_completed(result=..., rationale=...)

# Then complete assessment
assessment.mark_completed(user)
```

### 4. Use Descriptive Rationales
```python
assessment.overall_rationale = '''
Summary of key findings:
- Indicator A: Positive trend, no concerns
- Indicator B: Requires monitoring, approaching threshold
- Indicator C: Breached, immediate action needed

Recommendation: Implement mitigation plan for Indicator C while
monitoring B closely. Overall risk level remains acceptable.
'''
```

---

## Troubleshooting

### Issue: "Cannot save - scheduled date after assessment date"

**Cause:** Indicator's scheduled_assessment_date > parent assessment_date

**Solution:**
```python
# Adjust indicator date
indicator.scheduled_assessment_date = date_before_assessment
indicator.save()

# OR adjust assessment date
assessment.assessment_date = date_after_indicators
assessment.save()
```

### Issue: "Cannot complete assessment - indicators incomplete"

**Cause:** One or more indicators not marked as completed

**Solution:**
```python
# Find incomplete indicators
incomplete = assessment.linked_indicators.exclude(status='completed')
print(incomplete)

# Complete each one
for indicator in incomplete:
    indicator.mark_completed(result='...', rationale='...')
```

### Issue: ValidationError on save()

**Cause:** Model validation failing

**Solution:**
```python
# Skip validation if needed (use with caution!)
obj.save(skip_validation=True)

# OR fix the validation error
try:
    obj.save()
except ValidationError as e:
    print(e.message_dict)  # See what's wrong
```

---

## Testing Checklist

- [ ] Create assessment with linked indicators
- [ ] Try to complete assessment with incomplete indicators (should fail)
- [ ] Complete all indicators, then complete assessment (should succeed)
- [ ] Try to set indicator scheduled date after assessment date (should fail)
- [ ] View assessment detail page and verify all sections display correctly
- [ ] Check that indicator breakdown table shows all indicators
- [ ] Verify status badges display with correct colors
- [ ] Test that completion warnings appear when indicators incomplete
- [ ] Test that success message appears when all indicators completed
- [ ] Verify overall result and rationale display properly

---

## Migration Rollback (If Needed)

If you need to rollback this migration:

```bash
python manage.py migrate riskregister 0020_indicatorassessment_triggered_risk_assessment_and_more
```

**WARNING:** This will remove:
- risk_assessment field from RiskIndicator (data loss!)
- scheduled_assessment_date field
- status fields
- result and rationale fields
- All new validation logic

---

## Summary

This refactoring enforces a strict and traceable relationship between risk assessments and their constituent indicators, ensuring:

1. **Data Integrity:** One assessment → many indicators relationship
2. **Workflow Enforcement:** Indicators must be completed before assessment
3. **Schedule Validation:** Indicators scheduled before assessment date
4. **Complete Audit Trail:** Result and rationale at both indicator and assessment levels
5. **Clear UI Feedback:** Users see exactly what's preventing completion

The changes provide a robust framework for managing hierarchical risk assessments with full validation and traceability.

---

**End of Implementation Guide**
