# My Activities Feature

## Overview
A comprehensive activity tracking page that displays all assigned responsibilities for the logged-in user across risks, controls, and mitigations.

## Implementation Details

### 1. View Function
**Location:** `riskregister/views.py` - `my_activities()`

**Functionality:**
- Matches current user to RiskOwner by email or full name
- Retrieves all owned risks, controls, and assigned mitigations
- Calculates summary statistics (counts, overdue items)
- Provides filtered views by activity type

### 2. Template
**Location:** `riskregister/templates/riskregister/my_activities.html`

**Features:**
- Summary dashboard with 4 stat cards:
  - Risks Owned
  - Controls Owned
  - Mitigations Assigned
  - Overdue Items
  
- Tabbed interface with 4 views:
  - **All Activities:** Combined card view of all items
  - **Owned Risks:** Table view with risk details
  - **Owned Controls:** Table view with control effectiveness
  - **Assigned Mitigations:** Table view with progress tracking

**Visual Indicators:**
- Color-coded cards based on status/urgency
- Progress bars for mitigations and controls
- Badges for roles, statuses, and priorities
- Overdue highlighting in red
- Warning indicators for approaching due dates

### 3. URL Configuration
**Route:** `/my-activities/`
**Name:** `my_activities`
**Location:** `riskregister/urls.py`

### 4. Navigation
**Updated:** `templates/includes/sidenav.html`
- Added "My Activities" link with user-check icon
- Positioned between "Actions" and "Risk Matrix"
- Active state highlighting when on the page

## User Matching Logic

The system matches logged-in users to RiskOwner records using:
1. **Primary:** Email address match (case-insensitive)
2. **Fallback:** Full name match (first name + last name, case-insensitive)

If no RiskOwner match is found, the page displays empty state messages.

## Activity Types Tracked

### 1. Owned Risks
- **Criteria:** User is the Risk Owner
- **Display:** Shows risk title, score, department, category
- **Color Coding:**
  - Red border: High risk (score ≥ 15)
  - Yellow border: Medium risk (score ≥ 9)
  - Blue border: Low risk

### 2. Owned Controls
- **Criteria:** User is the Control Owner
- **Display:** Shows control name, type, effectiveness percentage
- **Color Coding:**
  - Green: Effectiveness ≥ 70%
  - Yellow: Effectiveness 50-69%
  - Red: Effectiveness < 50%

### 3. Assigned Mitigations
- **Criteria:** User is the Responsible Person
- **Display:** Shows strategy, action, due date, progress
- **Color Coding:**
  - Red border: Overdue
  - Yellow border: Due within 7 days
  - Green border: Complete
  - Blue border: Normal status

## Statistics Displayed

1. **Owned Risks Count:** Total number of risks owned
2. **Owned Controls Count:** Total active controls owned
3. **Assigned Mitigations Count:** Total mitigations assigned
4. **Overdue Count:** Number of overdue mitigations

## Key Features

### Progress Tracking
- Visual progress bars for mitigation completion percentage
- Control effectiveness displayed as percentage and bar
- Days overdue/remaining for mitigations

### Quick Actions
- Direct links to risk detail pages
- "Update" buttons for mitigations
- "View" buttons for all items

### Auto-Refresh
- Page automatically refreshes every 5 minutes to keep data current

### Responsive Design
- Bootstrap 5 grid layout
- Mobile-friendly cards and tables
- Gradient colored stat cards
- Hover effects on activity cards

## Usage

1. **Access:** Click "My Activities" in the sidebar navigation
2. **View Summary:** See overview statistics at the top
3. **Filter:** Use tabs to filter by activity type
4. **Take Action:** Click links to view details or update items
5. **Monitor:** Track overdue items highlighted in red

## Database Queries

**Efficient Data Loading:**
- Uses `select_related()` for foreign key optimization
- Orders results by relevance (risk score, effectiveness, due date)
- Filters out deleted/inactive items
- Single-pass calculation of derived properties

## Future Enhancements

Potential improvements:
- Email notifications for approaching due dates
- Export functionality for activity reports
- Activity history timeline
- Filtering by status, department, or date range
- Search functionality within activities
- Bulk actions for multiple items

## Testing

To test the feature:
1. Login with a user account that has a matching RiskOwner record
2. Navigate to `/my-activities/`
3. Verify statistics match actual database counts
4. Test each tab view
5. Click through to detail pages
6. Test with users who have no assigned activities

## Notes

- The RiskOwner model links to Department (one-to-one) but not directly to User
- User matching is done via email or name fields
- Empty states are shown when no activities are found
- All dates use Django's timezone-aware datetime handling
