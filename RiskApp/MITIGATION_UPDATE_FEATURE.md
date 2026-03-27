# Mitigation Update Feature

## Overview
Added comprehensive mitigation status update functionality with automatic risk reassessment triggering and audit trail logging.

## Changes Made

### 1. New Form: `MitigationUpdateForm` (forms.py)
- **Fields:**
  - `status`: Update mitigation status (Pending, In Progress, Complete)
  - `due_date`: Adjust due date if needed
  - `evidence`: Upload evidence documents
  - `progress_notes`: Document progress, challenges, or updates
  - `trigger_reassessment`: Checkbox to trigger risk reassessment

### 2. New View: `update_mitigation` (views.py)
**Location:** `/riskregister/mitigations/<mitigation_id>/update/`

**Features:**
- Updates mitigation status with validation
- Automatically logs all changes to ActivityLog
- Triggers special logging when mitigation is completed
- Optionally redirects to risk reassessment form
- Auto-triggers reassessment when mitigation is marked complete

**Audit Trail Logging:**
- `mitigation_updated`: Logs status changes with old/new values
- `mitigation_completed`: Special log when mitigation is completed
- `reassessment_triggered`: Logs when reassessment is initiated

### 3. New Template: `mitigation_update_form.html`
**Features:**
- Clean, user-friendly interface extending base.html
- Shows current risk and mitigation details
- Status guide sidebar with color-coded badges
- Best practices tips
- Evidence upload with current file display
- Reassessment trigger with clear explanations

### 4. URL Routing Update (urls.py)
Added route: `path('mitigations/<int:mitigation_id>/update/', views.update_mitigation, name='update_mitigation')`

### 5. Risk Detail Template Update (detailed.html)
- Added "Update Status" button next to each mitigation
- Added strategy badge display
- Added evidence link display
- Fixed status badge colors (changed 'completed' to 'complete' to match model)

## User Workflow

1. **View Risk Details** → Navigate to mitigation tab
2. **Click Edit Button** → Opens mitigation update form
3. **Update Status** → Select new status (Pending → In Progress → Complete)
4. **Add Progress Notes** → Document what was done
5. **Upload Evidence** → Attach supporting documents (optional)
6. **Trigger Reassessment** → Check box if risk should be reevaluated
7. **Submit** → 
   - Changes logged to audit trail
   - If completed or reassessment triggered → redirected to risk assessment form
   - Otherwise → returned to risk detail page

## Audit Trail Context

Each update creates audit log entries with:
```python
{
    'mitigation_id': <id>,
    'risk_id': <id>,
    'risk_number': 'R01FN',
    'old_status': 'pending',
    'new_status': 'in_progress',
    'progress_notes': '<user notes>',
    'trigger_reassessment': True/False
}
```

## Automatic Risk Reassessment

Reassessment is triggered when:
1. User manually checks "Trigger Risk Reassessment" checkbox
2. Mitigation status changes to "complete"

The system redirects to the risk assessment form where users can:
- Update likelihood and impact
- Document rationale for changes
- Link assessment to the mitigation completion

## Benefits

1. **Transparency**: Full audit trail of all mitigation activities
2. **Workflow Integration**: Seamless connection between mitigation and risk reassessment
3. **Progress Tracking**: Document progress with notes and evidence
4. **Risk Management**: Ensures risk ratings stay current as mitigations are completed
5. **Accountability**: Clear logging of who did what and when

## Testing Checklist

- [ ] Update mitigation status from Pending → In Progress
- [ ] Update mitigation status from In Progress → Complete
- [ ] Verify audit log entries are created
- [ ] Trigger manual reassessment via checkbox
- [ ] Complete mitigation and verify auto-redirect to assessment
- [ ] Upload evidence document
- [ ] Add progress notes
- [ ] Verify all logs appear in audit trail view
- [ ] Test with different user permissions
