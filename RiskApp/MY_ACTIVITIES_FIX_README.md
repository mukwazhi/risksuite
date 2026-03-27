# My Activities Page - User Profile Linking

## Issue
The My Activities page (http://127.0.0.1:8000/my-activities/) was not displaying any objects from the database because the logged-in Django user account was not linked to any RiskOwner profile in the database.

## Root Cause
The `my_activities` view matches Django User accounts to RiskOwner profiles using:
1. Email address (case-insensitive match)
2. Full name (first_name + last_name)

If no match is found, the page shows no activities.

### Specific Problem
- User `bmukwazhi` has email `mukwazh@gmail.com`
- No RiskOwner in the database has this email
- User has no first_name/last_name set, so name matching also fails

## Solution Applied

### 1. View Enhancement
Updated [views.py](riskregister/views.py#L3340) to handle supervisors without RiskOwner profiles:
- Supervisors (staff/superuser) can now see all RiskOwners
- If a supervisor has no personal RiskOwner profile, the page defaults to showing the first available RiskOwner's activities
- Users can then use the dropdown to select any team member

### 2. Template Improvements
Updated [my_activities.html](riskregister/templates/riskregister/my_activities.html) with:
- Clear warning message when supervisor account is not linked to a RiskOwner
- Helpful instructions to select team members from dropdown
- Better empty state messaging

### 3. Utility Scripts Created

#### check_user_data.py
Shows all users and risk owners with their data counts:
```bash
python check_user_data.py
```

#### test_my_activities.py
Tests the view logic for the current user:
```bash
python test_my_activities.py
```

#### link_users.py
Utility to link Django users to RiskOwner profiles:
```bash
# Show current mappings
python link_users.py

# Link user 1 to RiskOwner with email mra@gmail.com
python link_users.py link 1 mra@gmail.com

# Create a new RiskOwner for user 1 in department 5
python link_users.py create 1 5
```

## How to Fix for Your Account

### Option 1: Link to Existing RiskOwner (Recommended)
```bash
python link_users.py link 1 mra@gmail.com
```
This updates your user email to match an existing RiskOwner.

### Option 2: Create New RiskOwner
First, check available departments:
```bash
python manage.py shell -c "from riskregister.models import Department; [print(f'{d.id}: {d.name}') for d in Department.objects.all()]"
```

Then create RiskOwner:
```bash
python link_users.py create 1 <department_id>
```

### Option 3: Use as Supervisor
No action needed! The page now automatically shows the first RiskOwner's activities, and you can use the dropdown to view any team member's activities.

## Current State

### What Works Now
✅ Supervisors without profiles can view all team members' activities
✅ Dropdown filter allows viewing any RiskOwner's activities  
✅ Page shows clear messages about account linking status
✅ Default selection shows meaningful data instead of empty page

### What's Displayed
When visiting http://127.0.0.1:8000/my-activities/:
- **Summary cards** showing counts of risks, controls, and mitigations
- **All Activities tab** with cards for each item
- **Individual tabs** for risks, controls, and mitigations
- **User filter dropdown** for supervisors to view any team member

## Data Currently Available
```
Risk Owners in Database:
1. Mr A (mra@gmail.com) - Audit Dept - 7 Risks, 5 Controls, 7 Mitigations
2. Mr F (mrf@gmail.com) - Finance - 5 Risks, 0 Controls, 0 Mitigations  
3. Mr I (mri@gmail.com) - IT - 5 Risks, 0 Controls, 0 Mitigations
4. Mrs SHO (sho@who.com) - SHO - 1 Risk, 1 Control, 1 Mitigation
```

## Testing
Visit http://127.0.0.1:8000/my-activities/ and you should see:
- Warning message about account not being linked (if applicable)
- Dropdown to select team members
- Activities for the selected team member (default: Mr A)
- All tabs should show data when team member is selected
