# Inherent Risk Assessment & Weighted Controls Guide

## Overview

This guide explains the new integrated risk assessment features that enhance the risk management process with inherent risk rating, weighted internal controls, and automatic residual risk calculation.

## FEATURE 1: Inherent Risk Assessment

### What is Inherent Risk?

Inherent risk is the risk that exists **before** any controls are applied. It represents the "worst case" scenario if no mitigation measures were in place.

### How to Use

When creating or editing a risk, you'll now see two new fields:

#### Inherent Likelihood (1-5)
- **1 - Very Low**: Extremely unlikely to occur
- **2 - Low**: Unlikely to occur
- **3 - Medium**: May occur occasionally
- **4 - High**: Likely to occur
- **5 - Very High**: Almost certain to occur

#### Inherent Impact (1-5)
- **1 - Negligible**: Minimal impact on operations
- **2 - Minor**: Small impact, easily managed
- **3 - Moderate**: Noticeable impact requiring attention
- **4 - Major**: Significant impact affecting key operations
- **5 - Catastrophic**: Severe impact threatening organizational objectives

### Inherent Risk Score Calculation

```
Inherent Risk Score = Inherent Likelihood × Inherent Impact
```

**Example**: A risk with Inherent Likelihood of 4 (High) and Inherent Impact of 5 (Catastrophic) has an Inherent Risk Score of 20.

---

## FEATURE 2: Weighted Internal Controls

### What are Weighted Controls?

Controls are measures put in place to reduce risk. Each control has:

1. **Effectiveness** (0-100%): How well the control works
2. **Weight** (1-10): How important the control is
3. **Type**: How the control reduces risk

### Control Types and Their Effects

Each control type reduces risk differently:

#### 1. Preventive Controls
- **Purpose**: Prevent the risk from occurring
- **Reduction**: 80% to Likelihood, 20% to Impact
- **Examples**: Access controls, segregation of duties, authorization requirements

#### 2. Detective Controls
- **Purpose**: Detect when the risk has occurred
- **Reduction**: 30% to Likelihood, 70% to Impact
- **Examples**: Monitoring, reconciliations, audits, exception reports

#### 3. Corrective Controls
- **Purpose**: Correct the impact after the risk occurs
- **Reduction**: 10% to Likelihood, 90% to Impact
- **Examples**: Incident response procedures, disaster recovery plans, backup systems

#### 4. Directive Controls
- **Purpose**: Direct behavior to reduce risk
- **Reduction**: 50% to Likelihood, 50% to Impact
- **Examples**: Policies, procedures, training programs, guidance documents

### Weight Scale (1-10)

The weight determines the control's relative importance:

- **1-2**: Minimal importance (nice to have)
- **3-4**: Low importance (supporting control)
- **5-6**: Average importance (standard control)
- **7-8**: High importance (key control)
- **9-10**: Critical importance (essential control)

### Adding Controls to a Risk

1. Navigate to the risk detail page or admin interface
2. Click "Add Control"
3. Fill in the control details:
   - **Name**: Brief description (e.g., "Monthly reconciliation")
   - **Description**: Detailed explanation of how it works
   - **Control Type**: Select Preventive, Detective, Corrective, or Directive
   - **Effectiveness**: Use the slider to set 0-100%
   - **Weight**: Select 1-10 based on importance
   - **Weight Rationale**: Explain why you chose this weight
   - **Control Owner**: Who is responsible
   - **Frequency**: How often it runs (e.g., daily, monthly, continuous)

### Weighted Effectiveness Calculation

The system calculates a **weighted average** of all active controls:

```
Weighted Effectiveness = Σ(Effectiveness × Weight) / Σ(Weight)
```

**Example**:
- Control A: 80% effective, weight 8 → contribution = 640
- Control B: 60% effective, weight 5 → contribution = 300
- Control C: 90% effective, weight 10 → contribution = 900
- **Total**: (640 + 300 + 900) / (8 + 5 + 10) = 1840 / 23 = **80%**

---

## FEATURE 3: Residual Risk Calculation

### What is Residual Risk?

Residual risk is the risk that **remains after** controls are applied. It's the realistic current risk level.

### Automatic Calculation Process

The system automatically calculates residual risk by:

1. **Starting with Inherent Risk**
   - Uses the inherent likelihood and inherent impact you set

2. **Applying Control Effects**
   - Each control reduces risk based on its:
     - Type (determines likelihood vs impact reduction)
     - Effectiveness (0-100%)
     - Weight (relative importance)

3. **Calculating Weighted Reductions**
   ```
   For each control:
   - Weight Factor = Control Weight / Total Weight of All Controls
   - Effectiveness Factor = Control Effectiveness / 100
   - Type Factor = Control Type's likelihood/impact split
   
   Likelihood Reduction += Weight Factor × Effectiveness Factor × Type's Likelihood Factor
   Impact Reduction += Weight Factor × Effectiveness Factor × Type's Impact Factor
   ```

4. **Computing Residual Values**
   ```
   Residual Likelihood = Inherent Likelihood × (1 - Likelihood Reduction)
   Residual Impact = Inherent Impact × (1 - Impact Reduction)
   Residual Risk Score = Residual Likelihood × Residual Impact
   ```

5. **Risk Reduction Percentage**
   ```
   Risk Reduction % = ((Inherent Score - Residual Score) / Inherent Score) × 100
   ```

### Example Calculation

**Scenario**: Financial reporting risk

**Inherent Risk**:
- Inherent Likelihood: 4 (High)
- Inherent Impact: 5 (Catastrophic)
- **Inherent Risk Score**: 20

**Controls**:

1. **Automated reconciliation** (Preventive)
   - Effectiveness: 85%
   - Weight: 9
   - Reduces: 80% likelihood, 20% impact

2. **Monthly review** (Detective)
   - Effectiveness: 70%
   - Weight: 7
   - Reduces: 30% likelihood, 70% impact

3. **Backup procedures** (Corrective)
   - Effectiveness: 60%
   - Weight: 5
   - Reduces: 10% likelihood, 90% impact

**Calculation**:

Total Weight = 9 + 7 + 5 = 21

*For Control 1 (Preventive)*:
- Weight Factor = 9/21 = 0.43
- Effectiveness Factor = 0.85
- Likelihood Reduction Contribution = 0.43 × 0.85 × 0.80 = 0.29 (29%)
- Impact Reduction Contribution = 0.43 × 0.85 × 0.20 = 0.07 (7%)

*For Control 2 (Detective)*:
- Weight Factor = 7/21 = 0.33
- Effectiveness Factor = 0.70
- Likelihood Reduction Contribution = 0.33 × 0.70 × 0.30 = 0.07 (7%)
- Impact Reduction Contribution = 0.33 × 0.70 × 0.70 = 0.16 (16%)

*For Control 3 (Corrective)*:
- Weight Factor = 5/21 = 0.24
- Effectiveness Factor = 0.60
- Likelihood Reduction Contribution = 0.24 × 0.60 × 0.10 = 0.01 (1%)
- Impact Reduction Contribution = 0.24 × 0.60 × 0.90 = 0.13 (13%)

**Total Reductions**:
- Likelihood Reduction = 29% + 7% + 1% = 37%
- Impact Reduction = 7% + 16% + 13% = 36%

**Residual Risk**:
- Residual Likelihood = 4 × (1 - 0.37) = 4 × 0.63 = 2.52 → **3** (rounded)
- Residual Impact = 5 × (1 - 0.36) = 5 × 0.64 = 3.2 → **3** (rounded)
- **Residual Risk Score** = 3 × 3 = **9**

**Risk Reduction**:
- Risk Reduction % = (20 - 9) / 20 × 100 = **55%**

---

## Viewing Risk Calculations

### In the Risk Detail View

The risk detail page displays:

1. **Inherent Risk Section**
   - Inherent Likelihood & Impact ratings
   - Inherent Risk Score
   - Risk matrix visualization

2. **Controls Summary**
   - List of all controls with their effectiveness and weight
   - Weighted average effectiveness
   - Control type breakdown

3. **Residual Risk Section**
   - Calculated residual likelihood & impact
   - Residual risk score
   - Risk reduction percentage
   - Comparison with inherent risk

4. **Risk Movement Indicator**
   - Visual representation of risk before and after controls
   - Color-coded risk levels

### Using the API/Properties

In code, you can access:

```python
risk = Risk.objects.get(pk=1)

# Inherent risk
inherent_score = risk.inherent_risk_score  # e.g., 20

# Control effectiveness
control_effectiveness = risk.get_weighted_control_effectiveness()  # e.g., 78.5%

# Residual risk calculation
residual_data = risk.calculate_residual_risk()
# Returns dict with:
# - residual_likelihood
# - residual_impact
# - residual_score
# - risk_reduction_pct
# - control_effectiveness
# - likelihood_reduction
# - impact_reduction

# Quick properties
residual_score = risk.residual_risk_score
reduction_pct = risk.risk_reduction_percentage
```

---

## Best Practices

### 1. Setting Inherent Risk
- Always assess inherent risk **first**, before thinking about controls
- Consider the worst-case scenario
- Be consistent across similar risks
- Document your reasoning

### 2. Defining Control Weights
- Use a consistent framework across your organization
- Document weight criteria (what makes a control weight 8 vs 10?)
- Consider:
  - Financial impact if control fails
  - Regulatory requirements
  - Complexity of the risk area
  - Dependencies on other controls

### 3. Measuring Control Effectiveness
- Base effectiveness on:
  - Testing results
  - Historical performance
  - Control maturity
  - Resource adequacy
- Update regularly as controls mature or degrade
- Document test results

### 4. Choosing Control Types
- Preventive controls should be your first line of defense
- Detective controls catch what preventive controls miss
- Corrective controls minimize damage
- Directive controls establish the framework
- Most effective control environments use a **combination** of all types

### 5. Regular Review
- Review inherent risk annually or when business context changes
- Test control effectiveness regularly
- Update effectiveness ratings based on test results
- Reassess control weights if priorities shift

---

## Troubleshooting

### "My residual risk score seems wrong"

**Check**:
1. Are all controls marked as `is_active=True`?
2. Is the inherent risk set correctly?
3. Are control types appropriate for what they do?
4. Are effectiveness percentages realistic?

### "Risk reduction percentage is 0%"

**Possible causes**:
- No inherent risk set (system falls back to current risk)
- All controls have 0% effectiveness
- All controls are inactive

### "Controls don't seem to affect residual risk"

**Check**:
- Control effectiveness values
- Control weights (all zeros?)
- Control active status
- Inherent risk values are set

---

## Migration Instructions

### Step 1: Run Migration

```bash
python manage.py migrate riskregister 0023_inherent_risk_and_controls
```

### Step 2: Set Inherent Risk for Existing Risks

For existing risks, you should:

1. Review each risk
2. Determine what the inherent likelihood and impact would be without controls
3. Update the `inherent_likelihood` and `inherent_impact` fields

**Quick Script** (optional):
```python
from riskregister.models import Risk

# Set inherent risk = current risk for all existing risks as a baseline
for risk in Risk.objects.all():
    if not risk.inherent_likelihood:
        risk.inherent_likelihood = risk.likelihood
    if not risk.inherent_impact:
        risk.inherent_impact = risk.impact
    risk.save()
```

### Step 3: Add Controls

Document existing controls by:
1. Identifying what controls are currently in place
2. Creating Control records in the system
3. Setting appropriate effectiveness and weights

---

## API Endpoints (for future development)

### Suggested endpoints for controls management:

```
GET    /api/risks/{risk_id}/controls/          # List all controls
POST   /api/risks/{risk_id}/controls/          # Add new control
GET    /api/risks/{risk_id}/controls/{id}/     # Get control detail
PUT    /api/risks/{risk_id}/controls/{id}/     # Update control
DELETE /api/risks/{risk_id}/controls/{id}/     # Delete control
GET    /api/risks/{risk_id}/residual-risk/     # Get residual risk calculation
```

---

## Support

For questions or issues with the inherent risk and controls features:

1. Check this documentation first
2. Review the model code in `models.py` (Risk and Control classes)
3. Check the admin interface for debugging
4. Contact the development team

---

## Version History

- **v1.0** (January 2026): Initial release
  - Inherent risk assessment
  - Weighted controls
  - Residual risk calculation
  - Control types with differential effects
