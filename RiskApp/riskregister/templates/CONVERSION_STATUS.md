# Template Conversion Status

## Overview
This document tracks the conversion of RiskMate ERP templates to use the new base template structure with consistent navigation.

## Completed Conversions ✅

### Base Templates
- ✅ `base.html` - Main base with sidebar navigation
- ✅ `base_nosidebar.html` - Base with topnav only (for forms/full-width pages)
- ✅ `includes/topnav.html` - Reusable top navigation component
- ✅ `includes/sidenav.html` - Reusable sidebar navigation component

### Application Templates
- ✅ `riskregister/risk_form.html` - Risk creation form (uses base_nosidebar)
- ✅ `riskregister/delete_confirm.html` - Delete confirmation modal (uses base_nosidebar)
- ✅ `riskregister/reject_confirm.html` - Rejection form (uses base_nosidebar)
- ✅ `example_page.html` - Documentation example page

## Templates Requiring Conversion 🔄

### High Priority (User-Facing Pages)
- 🔄 `Dashboard.html` - Main dashboard (already has navigation, needs cleanup)
- 🔄 `riskregister/Viewall.html` - All risks list view
- 🔄 `riskregister/actions_dashboard.html` - Actions dashboard
- 🔄 `riskregister/workflow_risks.html` - Workflow pages (parked/pending/approved/rejected)
- 🔄 `riskregister/view_risk.html` - Risk detail view
- 🔄 `riskregister/detailedView.html` - Detailed risk view

### Medium Priority (Forms & Data Entry)
- 🔄 `riskregister/mitigation_form.html` - Mitigation action form
- 🔄 `riskregister/assessment_form.html` - Risk assessment form
- 🔄 `riskregister/indicator_assessment_form.html` - Indicator assessment
- 🔄 `riskregister/schedule_form.html` - Schedule form
- 🔄 `riskregister/generate_schedules_form.html` - Generate schedules

### Low Priority (Reports & History)
- 🔄 `riskregister/indicator_assessment_history.html` - Assessment history
- 🔄 `reporting.html` - Reporting page
- 🔄 `reports.html` - Reports list
- 🔄 `reportwriter.html` - Report writer
- 🔄 `riskKpi.html` - Risk KPI dashboard

### Utility Templates  
- ✅ `riskregister/login.html` - Already has no navigation (auth page)
- 🔄 `home.html` - Landing page
- 🔄 `home2.html` - Alternative home
- 🔄 `register.html` - Registration page

## Conversion Guide

### For Pages with Sidebar (List/Dashboard Pages)

**Before:**
```django
<!DOCTYPE html>
<html lang="en">
<head>
    <title>My Page</title>
    <!-- CSS -->
</head>
<body>
    <!-- Full navigation code repeated -->
    <!-- Sidebar code repeated -->
    <div class="container">
        <!-- Content -->
    </div>
</body>
</html>
```

**After:**
```django
{% extends 'base.html' %}

{% block title %}My Page - RiskMate ERP{% endblock %}

{% block extra_styles %}
<style>
    /* Page-specific styles only */
</style>
{% endblock %}

{% block content %}
<!-- Page header with breadcrumb -->
<div class="d-flex justify-content-between align-items-center mt-3 mb-4">
    <div>
        <h1 class="h3 fw-bold mb-1">Page Title</h1>
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb mb-0">
                <li class="breadcrumb-item"><a href="{% url 'dashboard' %}">Home</a></li>
                <li class="breadcrumb-item active">Page Title</li>
            </ol>
        </nav>
    </div>
</div>

<!-- Your content here -->

{% endblock %}
```

### For Forms and Modal Pages (Full-Width)

**After:**
```django
{% extends 'base_nosidebar.html' %}

{% block title %}Form Title - RiskMate ERP{% endblock %}

{% block extra_styles %}
<style>
    /* Form-specific styles */
</style>
{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mt-3 mb-4">
    <div>
        <h1 class="h3 fw-bold mb-1">Form Title</h1>
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb mb-0">
                <li class="breadcrumb-item"><a href="{% url 'dashboard' %}">Home</a></li>
                <li class="breadcrumb-item active">Form</li>
            </ol>
        </nav>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-body">
        <!-- Form content -->
    </div>
</div>
{% endblock %}
```

## Steps to Convert a Template

1. **Backup Original** (optional but recommended)
   ```bash
   cp original.html original.html.bak
   ```

2. **Choose Base Template**
   - Use `base.html` for list views, dashboards, data tables
   - Use `base_nosidebar.html` for forms, modal pages, detail views

3. **Replace Header**
   - Remove `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` tags
   - Replace with `{% extends 'base.html' %}` or `{% extends 'base_nosidebar.html' %}`
   - Add `{% block title %}` for page title

4. **Move Styles**
   - Extract page-specific styles from `<style>` tags
   - Place in `{% block extra_styles %}`
   - Remove global styles (already in base)

5. **Wrap Content**
   - Remove navigation HTML (topnav and sidebar)
   - Wrap main content in `{% block content %}`
   - Add breadcrumb navigation
   - Ensure proper page header structure

6. **Update URLs**
   - Update hardcoded URLs to use `{% url 'name' %}` tags
   - Fix any relative paths

7. **Remove Footer**
   - Remove `</body>` and `</html>` closing tags
   - Close `{% endblock %}` instead

8. **Test**
   - Check page renders correctly
   - Verify navigation active states
   - Test responsive behavior

## Common Issues & Solutions

### Issue: Styles Not Applied
**Solution:** Check if styles are in `{% block extra_styles %}` not before template tags

### Issue: Navigation Not Showing
**Solution:** Ensure using correct base template (`base.html` has sidebar, `base_nosidebar.html` doesn't)

### Issue: Active Link Not Highlighting
**Solution:** Check URL pattern name matches in `urls.py`

### Issue: Layout Breaking
**Solution:** Remove container divs that wrap content - base template already has proper structure

## Context Variables

Templates using base templates should provide:
- `user` - Current user (automatic with @login_required)
- `parked_count`, `pending_count`, `approved_count`, `rejected_count` - For badge counts
- `total_risks`, `high_count` - For sidebar stats

Add to view context:
```python
context = {
    'parked_count': Risk.objects.filter(status='parked').count(),
    'pending_count': Risk.objects.filter(status='pending').count(),
    'approved_count': Risk.objects.filter(status='approved').count(),
    'rejected_count': Risk.objects.filter(status='rejected').count(),
    # ... your page data
}
```

## Benefits of Conversion

✅ **Consistency** - All pages have identical navigation
✅ **Maintainability** - Navigation changes in one place
✅ **Active State** - Automatic highlighting of current page
✅ **Role-Based** - Admin features auto-hide for non-superusers
✅ **Responsive** - Mobile-friendly navigation built-in
✅ **Cleaner Code** - Less duplication, easier to read

## Next Steps

1. Convert high-priority templates (Dashboard, Viewall, actions_dashboard)
2. Update views to provide required context variables
3. Test each converted page thoroughly
4. Remove `.bak` backup files once confirmed working
5. Update remaining templates progressively

## Support

For questions or issues with template conversion:
- See `example_page.html` for reference implementation
- Check `TEMPLATE_README.md` for detailed component documentation
- Review base templates for available blocks and features
