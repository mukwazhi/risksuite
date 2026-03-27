# Inherent Risk & Weighted Controls - Implementation Summary

## What Was Added

### 1. Database Models

#### Risk Model Enhancements
- Added `inherent_likelihood` (1-5 scale) - risk without controls
- Added `inherent_impact` (1-5 scale) - impact without controls
- Added property `inherent_risk_score` - calculated as likelihood × impact
- Added method `get_weighted_control_effectiveness()` - calculates weighted average
- Added method `calculate_residual_risk()` - comprehensive residual risk calculation
- Added properties for easy access: `residual_likelihood`, `residual_impact`, `residual_risk_score`, `risk_reduction_percentage`

#### New Control Model
Complete internal controls management with:
- `risk` - ForeignKey to Risk
- `name` - control description
- `description` - detailed explanation
- `control_type` - choices: preventive/detective/corrective/directive
- `effectiveness` - Decimal 0-100%
- `weight` - Integer 1-10 (with descriptive choices)
- `weight_rationale` - explanation for weight selection
- `control_owner` - ForeignKey to RiskOwner
- `frequency` - how often control executes
- `last_tested_date` - testing tracking
- `test_results` - test documentation
- `is_active` - enable/disable control
- Audit fields: created_at, updated_at, created_by

### 2. Forms

#### RiskForm Updates
- Added `inherent_likelihood` field with descriptive choices (1-Very Low through 5-Very High)
- Added `inherent_impact` field with descriptive choices (1-Negligible through 5-Catastrophic)
- Updated help texts and labels
- Custom widgets for better UX

#### New ControlForm
- Complete form for control management
- Effectiveness slider (0-100%) with real-time percentage display
- Weight dropdown with descriptive labels
- All control fields included
- Form validation

#### ControlFormSet
- Inline formset for managing multiple controls per risk
- Supports add, edit, delete operations
- Minimum 0 controls, extra=1 for easy adding

### 3. Admin Interface

#### Updated RiskAdmin
- Added "Inherent Risk Assessment" fieldset
- Included ControlInline for managing controls
- Updated field ordering and organization

#### New ControlAdmin
- Full admin interface for Control model
- List display with risk link, effectiveness badges, weight display
- Filters by type, weight, active status, department
- Custom display methods for effectiveness and weighted contribution
- Actions: activate, deactivate, mark for testing
- Comprehensive fieldsets

### 4. Migration

**File**: `0023_inherent_risk_and_controls.py`
- Adds inherent_likelihood to Risk model (nullable)
- Adds inherent_impact to Risk model (nullable)
- Creates Control model with all fields
- Sets up relationships and indexes

## How It Works

### Control Type Effects on Risk Reduction

Each control type has a specific reduction pattern:

| Control Type | Likelihood Reduction | Impact Reduction | Use Case |
|-------------|---------------------|------------------|----------|
| Preventive  | 80%                | 20%              | Stops risk from occurring |
| Detective   | 30%                | 70%              | Finds risk after it occurs |
| Corrective  | 10%                | 90%              | Fixes damage after occurrence |
| Directive   | 50%                | 50%              | Guides behavior equally |

### Calculation Flow

```
1. User sets Inherent Risk (before controls)
   ├─ Inherent Likelihood (1-5)
   └─ Inherent Impact (1-5)
   
2. User adds Controls
   ├─ Each control has:
   │  ├─ Type (preventive/detective/corrective/directive)
   │  ├─ Effectiveness (0-100%)
   │  └─ Weight (1-10)
   
3. System calculates Weighted Control Effectiveness
   ├─ Formula: Σ(Effectiveness × Weight) / Σ(Weight)
   └─ Example: (80×8 + 60×5 + 90×10) / (8+5+10) = 80%
   
4. System applies Type-Specific Reductions
   ├─ Each control reduces based on its type
   ├─ Weighted by importance (weight)
   ├─ Scaled by effectiveness
   └─ Accumulates across all active controls
   
5. System calculates Residual Risk
   ├─ Residual Likelihood = Inherent × (1 - Likelihood Reduction)
   ├─ Residual Impact = Inherent × (1 - Impact Reduction)
   └─ Residual Score = Residual Likelihood × Residual Impact
   
6. System shows Risk Reduction %
   └─ ((Inherent Score - Residual Score) / Inherent Score) × 100
```

## File Changes

### Modified Files
1. `riskregister/models.py`
   - Added inherent risk fields to Risk model (lines 137-151)
   - Added calculation methods (lines 192-354)
   - Added Control model (lines 1072-1234)

2. `riskregister/forms.py`
   - Updated RiskForm with inherent risk fields (lines 1-39)
   - Added ControlForm (lines 42-110)
   - Added ControlFormSet (lines 113-120)

3. `riskregister/admin.py`
   - Updated imports to include Control
   - Added ControlInline (lines 48-53)
   - Updated RiskAdmin fieldsets (lines 109-130)
   - Updated RiskAdmin inlines (line 131)
   - Added ControlAdmin class (lines 165-245)

### New Files
1. `riskregister/migrations/0023_inherent_risk_and_controls.py`
   - Database migration for new fields and model

2. `INHERENT_RISK_AND_CONTROLS_GUIDE.md`
   - Comprehensive user guide
   - Examples and calculations
   - Best practices
   - Troubleshooting

3. `INHERENT_RISK_AND_CONTROLS_SUMMARY.md` (this file)
   - Technical implementation summary

## Next Steps

### To Deploy

1. **Run Migration**
   ```bash
   cd c:\Users\hp\PycharmProjects\RiskMate\RiskApp
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Update Existing Risks** (optional but recommended)
   ```python
   python manage.py shell
   >>> from riskregister.models import Risk
   >>> for risk in Risk.objects.all():
   ...     if not risk.inherent_likelihood:
   ...         risk.inherent_likelihood = risk.likelihood
   ...         risk.inherent_impact = risk.impact
   ...         risk.save()
   ```

3. **Test in Admin Interface**
   - Navigate to Django admin
   - Open a risk
   - Set inherent likelihood and impact
   - Add controls via the inline form
   - Verify calculations

### To Integrate into Views/Templates

You can now access these features in your views:

```python
from riskregister.models import Risk, Control

# Get a risk
risk = Risk.objects.get(pk=1)

# Access inherent risk
print(f"Inherent Risk Score: {risk.inherent_risk_score}")

# Get controls
controls = risk.controls.filter(is_active=True)
for control in controls:
    print(f"{control.name}: {control.effectiveness}% (weight {control.weight})")

# Get weighted effectiveness
effectiveness = risk.get_weighted_control_effectiveness()
print(f"Overall Control Effectiveness: {effectiveness:.1f}%")

# Get residual risk calculation
residual = risk.calculate_residual_risk()
print(f"Residual Risk Score: {residual['residual_score']}")
print(f"Risk Reduction: {residual['risk_reduction_pct']:.1f}%")

# Quick access properties
print(f"Residual Likelihood: {risk.residual_likelihood}")
print(f"Residual Impact: {risk.residual_impact}")
```

### To Add to Templates

Example template code to display controls:

```django
{% if risk.inherent_likelihood and risk.inherent_impact %}
<div class="card">
    <div class="card-header">
        <h5>Inherent Risk (Before Controls)</h5>
    </div>
    <div class="card-body">
        <p>Likelihood: {{ risk.inherent_likelihood }} / Impact: {{ risk.inherent_impact }}</p>
        <p>Inherent Risk Score: <strong>{{ risk.inherent_risk_score }}</strong></p>
    </div>
</div>

<div class="card mt-3">
    <div class="card-header">
        <h5>Controls</h5>
    </div>
    <div class="card-body">
        {% with controls=risk.controls.all %}
            {% if controls %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Control</th>
                            <th>Type</th>
                            <th>Effectiveness</th>
                            <th>Weight</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for control in controls %}
                        <tr>
                            <td>{{ control.name }}</td>
                            <td>{{ control.get_control_type_display }}</td>
                            <td>{{ control.effectiveness }}%</td>
                            <td>{{ control.weight }}/10</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <p><strong>Weighted Average Effectiveness:</strong> {{ risk.get_weighted_control_effectiveness|floatformat:1 }}%</p>
            {% else %}
                <p class="text-muted">No controls defined yet.</p>
            {% endif %}
        {% endwith %}
    </div>
</div>

<div class="card mt-3">
    <div class="card-header">
        <h5>Residual Risk (After Controls)</h5>
    </div>
    <div class="card-body">
        {% with residual=risk.calculate_residual_risk %}
            <p>Residual Likelihood: {{ residual.residual_likelihood }} / Impact: {{ residual.residual_impact }}</p>
            <p>Residual Risk Score: <strong>{{ residual.residual_score }}</strong></p>
            <p class="text-success">Risk Reduction: <strong>{{ residual.risk_reduction_pct }}%</strong></p>
        {% endwith %}
    </div>
</div>
{% endif %}
```

## Testing Checklist

- [ ] Migration runs successfully
- [ ] Can add inherent risk values to a risk in admin
- [ ] Can add controls to a risk in admin
- [ ] Controls display correctly in admin list view
- [ ] Effectiveness slider works
- [ ] Weight dropdown displays correctly
- [ ] Residual risk calculation returns correct values
- [ ] Risk reduction percentage calculates correctly
- [ ] Control type dropdown includes all 4 types
- [ ] Can activate/deactivate controls
- [ ] Can delete controls
- [ ] Control formset validation works
- [ ] Weighted effectiveness calculation is accurate

## Support Information

**Models Location**: `riskregister/models.py`
- Risk model: lines 130-360
- Control model: lines 1072-1234

**Forms Location**: `riskregister/forms.py`
- RiskForm: lines 4-39
- ControlForm: lines 42-110
- ControlFormSet: lines 113-120

**Admin Location**: `riskregister/admin.py`
- ControlAdmin: lines 165-245
- RiskAdmin updates: lines 109-131

**Documentation**: `INHERENT_RISK_AND_CONTROLS_GUIDE.md`

## Version

**Feature Version**: 1.0
**Date**: January 16, 2026
**Migration**: 0023_inherent_risk_and_controls
