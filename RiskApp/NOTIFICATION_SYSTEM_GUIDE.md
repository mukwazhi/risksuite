# Notification System Documentation

## Overview
The RiskMate ERP notification system provides a comprehensive, rule-based alert mechanism that drives user action while minimizing alert fatigue. The system handles two critical workflows:
1. **Indicator Assessment Schedules** - Notifications for upcoming and overdue indicator measurements
2. **Mitigation Due Dates** - Alerts for mitigation actions approaching or past their due dates

## Key Features

### 1. Rule-Based Configuration (Superuser Only)
Superusers can define notification rules with:
- **Rule Types**: Mitigation Due Date, Assessment Schedule, Risk Level Changes, Indicator Breaches
- **Conditions**: Is Overdue, Due in X Days, Overdue by X Days, No Assessment for X Days
- **Risk Level Filters**: Only trigger for specific risk levels (Low, Medium, High, Critical)
- **Recipients**: Risk Owner, Mitigation Responsible, Department Head, All Managers, Specific User
- **Channels**: Email and/or In-App notifications
- **Priority Levels**: Urgent, High, Medium, Low
- **Message Templates**: Customizable with placeholders

### 2. User Preferences (Superuser Managed)
**IMPORTANT**: Only superusers can configure notification preferences. Regular users are subject to the preferences set for them by superusers.

Superusers can configure for each user:
- **Channels**: Enable/disable email and in-app notifications
- **Frequency**: Immediate, Twice Daily, Daily Digest, Weekly
- **Risk Level Threshold**: Only receive notifications for risks above a certain level
- **Notification Types**: Toggle specific types (mitigations, assessments, risk changes, breaches)
- **Timing**: Configure advance notice days for mitigations and assessments
- **Quiet Hours**: Set time ranges where notifications won't be sent

**Default Behavior**: If a user has no preferences configured, they will receive all notifications according to the active notification rules.

### 3. Conditional Logic
The system supports sophisticated conditional logic:
- **If risk is High → notify manager immediately**
- **If overdue >3 days → notify department head**
- **If indicator breached → notify risk owner urgently**
- **If assessment due in 3 days → notify responsible person**

## System Components

### Models

#### NotificationRule
Defines the rules for generating notifications:
- `name`: Rule identifier
- `rule_type`: Type of event (mitigation_due, assessment_schedule, etc.)
- `condition`: When to trigger (overdue, due_in_days, etc.)
- `condition_value`: Numeric value for condition (e.g., days)
- `risk_level_filter`: Optional filter by risk level
- `recipient_type`: Who receives the notification
- `priority`: Rule processing priority (0-100)
- `notify_via_email`: Email notification flag
- `notify_in_app`: In-app notification flag
- `message_template`: Customizable message with placeholders

#### NotificationPreference
User-specific notification settings:
- `user`: Associated user
- `notification_frequency`: How often to send (immediate, daily, weekly)
- `minimum_risk_level`: Minimum risk level to notify
- `enable_email_notifications`: Email channel toggle
- `enable_in_app_notifications`: In-app channel toggle
- `notify_mitigation_due`: Mitigation notifications toggle
- `notify_assessment_schedule`: Assessment notifications toggle
- `notify_risk_changes`: Risk level change notifications toggle
- `notify_indicator_breach`: Indicator breach notifications toggle
- `days_before_due_mitigation`: Advance notice for mitigations
- `days_before_due_assessment`: Advance notice for assessments
- `quiet_hours_start/end`: Time range for no notifications

#### Notification
Individual notification instances:
- `recipient`: User receiving the notification
- `notification_type`: Type of notification
- `priority`: Urgency level
- `title`: Notification title
- `message`: Detailed message
- `risk/mitigation/indicator/schedule`: Related objects
- `action_url`: Link to take action
- `is_read`: Read status
- `is_emailed`: Email sent status
- `generated_by_rule`: Rule that created this notification
- `expires_at`: Auto-dismiss date

### Notification Engine

Located in `riskregister/utils/notifications.py`, the NotificationEngine:
1. Processes all active notification rules
2. Evaluates conditions against current data
3. Filters by risk level if specified
4. Determines appropriate recipients
5. Checks user preferences before sending
6. Creates notifications and sends emails
7. Prevents duplicate notifications

### Management Command

`python manage.py process_notifications`

Options:
- `--send-digests`: Send daily/weekly digest emails
- `--dry-run`: Test mode without creating notifications

**Recommended Schedule**:
- Run every 15-30 minutes via cron or Windows Task Scheduler
- Example cron: `*/15 * * * * cd /path/to/project && python manage.py process_notifications`
- Example with digests: `0 8 * * * cd /path/to/project && python manage.py process_notifications --send-digests`

## Usage Guide

### Permission Model

**IMPORTANT: User Access Control**

The notification system follows a strict permission model:

1. **Superusers** (Administrators):
   - Create, edit, and delete notification rules
   - Configure notification preferences for ANY user
   - Test notification rules manually
   - View all notification activity logs
   - Access: `/notifications/rules/` and `/notifications/preferences/`

2. **Regular Users** (Staff):
   - **CANNOT** configure their own notification preferences
   - **CANNOT** modify notification rules
   - Subject to preferences set by superusers
   - Can view and manage their own notifications
   - Access: `/notifications/` (notification center only)

3. **Default Behavior**:
   - If a user has NO preferences configured, they receive ALL notifications matching active rules
   - Superusers must explicitly configure preferences to filter notifications for users
   - This ensures critical notifications are never missed due to unconfigured settings

### For Superusers

#### Configuring User Preferences

1. Navigate to **Administration → User Preferences**
2. Select the user from the list
3. Configure their preferences:
   - **Channels**: Enable/disable email and in-app
   - **Frequency**: Immediate, Twice Daily, Daily, or Weekly digest
   - **Risk Level Threshold**: Minimum risk level (Low, Medium, High, Critical)
   - **Notification Types**: Toggle categories (mitigations, assessments, changes, breaches)
   - **Timing**: Days before due for advance notice
   - **Quiet Hours**: Do-not-disturb time range
4. Click **Save**
5. Success message confirms: "Notification preferences for [User Name] have been saved successfully!"

**Best Practice**: Configure preferences for users based on their role:
- **Department Heads**: High/Critical risks, immediate, all types
- **Risk Owners**: Medium+ risks, twice daily, relevant risks only
- **Staff Members**: High risks only, daily digest, limited types

#### Creating Notification Rules

1. Navigate to **Administration → Notification Rules**
2. Click **Add New Rule**
3. Configure the rule:
   - **Name**: "High Risk Mitigation Overdue Alert"
   - **Rule Type**: Mitigation Due Date
   - **Condition**: Overdue by X Days
   - **Condition Value**: 3
   - **Risk Level Filter**: High
   - **Recipient Type**: Department Head
   - **Priority**: 80
   - **Channels**: Email + In-App
   - **Message Template**: 
     ```
     High priority mitigation for risk "{risk_title}" is overdue by {days} days. 
     Responsible: {responsible_person}. 
     Please take immediate action.
     ```
4. **Activate** the rule

#### Example Rules

**Rule 1: Critical Risk Mitigation Due Soon**
- Condition: Due in 3 days
- Risk Level: Critical
- Recipients: Risk Owner + All Managers
- Priority: Urgent
- Message: "URGENT: Critical risk mitigation due in {days} days for {risk_title}"

**Rule 2: Assessment Overdue**
- Condition: Overdue
- Type: Assessment Schedule
- Recipients: Risk Owner
- Priority: High
- Message: "Risk assessment for {risk_title} is overdue. Please complete assessment."

**Rule 3: Indicator Breach**
- Type: Indicator Breach
- Recipients: Risk Owner
- Priority: Urgent
- Message: "Indicator for {risk_title} has breached tolerance threshold. Immediate review required."

### For Regular Users

**Note**: Regular users CANNOT configure their own notification preferences. All settings are managed by superusers.

#### Viewing Notifications

1. Click the **Bell Icon** in the top navigation
2. View unread count badge
3. Filter by type, priority, or read/unread
4. Click **Take Action** to navigate to related item
5. Mark as read or delete notifications

#### Understanding Your Notifications

Your notifications are controlled by:
1. **Active notification rules** set by administrators
2. **Your user preferences** configured by administrators
3. **Your role** in risk ownership or mitigation responsibility

If you receive too many or too few notifications, contact your system administrator to adjust your preferences.

## Alert Fatigue Mitigation

The system reduces alert fatigue through:

1. **User Preferences**: Users control what they receive
2. **Risk Level Filtering**: Only notify for significant risks
3. **Frequency Options**: Digest modes reduce constant interruptions
4. **Quiet Hours**: Respect work-life boundaries
5. **Duplicate Prevention**: Same notification not sent multiple times
6. **Priority-Based**: Urgent items stand out from routine alerts
7. **Expiration**: Old notifications auto-dismiss
8. **Conditional Logic**: Only notify when truly needed

## API Endpoints

### User Endpoints
- `GET /notifications/` - Notification center
- `GET /notifications/preferences/` - User preferences page
- `POST /notifications/<id>/mark-read/` - Mark notification as read
- `POST /notifications/mark-all-read/` - Mark all as read
- `POST /notifications/<id>/delete/` - Delete notification
- `GET /notifications/api/unread-count/` - JSON API for unread count

### Admin Endpoints (Superuser Only)
- `GET /notifications/rules/` - List all rules
- `GET /notifications/rules/create/` - Create new rule
- `GET /notifications/rules/<id>/edit/` - Edit rule
- `POST /notifications/rules/<id>/delete/` - Delete rule
- `POST /notifications/rules/<id>/toggle/` - Activate/deactivate rule
- `POST /notifications/rules/test/` - Manually trigger rule processing

## Technical Details

### Message Template Placeholders
- `{risk_title}` - Title of the risk
- `{risk_id}` - Risk identifier
- `{due_date}` - Due date (formatted)
- `{days}` - Number of days (overdue or until due)
- `{responsible_person}` - Name of responsible person
- `{department}` - Department name

### Database Indexes
Optimized queries with indexes on:
- `recipient + is_read + created_at` (notification queries)
- `notification_type + created_at` (filtering)

### Email Configuration
Requires `settings.py` configuration:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'RiskMate ERP <noreply@riskmate.com>'
```

## Best Practices

1. **Start Simple**: Begin with a few high-priority rules
2. **Test Rules**: Use dry-run mode to verify behavior
3. **Monitor Feedback**: Adjust based on user complaints
4. **Avoid Over-Notification**: Too many alerts = ignored alerts
5. **Use Risk Filters**: Don't notify for low-risk items
6. **Clear Messages**: Make action items obvious
7. **Regular Review**: Deactivate ineffective rules
8. **Respect Preferences**: Honor user choices

## Troubleshooting

### Notifications Not Sending
1. Check rule is active
2. Verify condition logic
3. Check user preferences
4. Confirm quiet hours settings
5. Review management command logs

### Too Many Notifications
1. Increase risk level threshold
2. Switch to digest mode
3. Adjust condition values (more days)
4. Disable less important types
5. Review and deactivate noisy rules

### Email Not Working
1. Check EMAIL settings in settings.py
2. Verify SMTP credentials
3. Test with Django shell: `python manage.py shell`
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```
4. Check spam folder
5. Review email logs

## Future Enhancements

Potential additions:
- SMS notifications via Twilio
- Slack/Teams integration
- Push notifications for mobile app
- Machine learning for alert prioritization
- Analytics dashboard for notification effectiveness
- Custom notification templates per user
- Notification history and audit trail

## Support

For issues or questions:
- Contact: System Administrator
- Documentation: This file
- Logs: `riskregister/utils/notifications.py` (logger)
- Admin: Django admin panel → Notifications section

---

**Version**: 1.0  
**Last Updated**: January 4, 2026  
**Author**: RiskMate Development Team
