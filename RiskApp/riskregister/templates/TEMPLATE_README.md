# RiskMate ERP - Template Structure Documentation

## Overview
This document explains the base template structure for consistent navigation across all pages.

## Directory Structure
```
templates/
├── base.html                    # Main base template (with sidebar)
├── base_nosidebar.html         # Base template without sidebar
├── example_page.html           # Example usage template
├── includes/
│   ├── topnav.html            # Top navigation bar component
│   └── sidenav.html           # Sidebar navigation component
└── riskregister/
    └── (existing templates)
```

## Base Templates

### 1. base.html
Main base template that includes both top navigation and sidebar navigation.

**Use for:**
- Dashboard pages
- List views
- Pages that benefit from sidebar navigation

**Features:**
- Responsive top navigation bar
- Collapsible sidebar (hidden on mobile)
- User profile dropdown
- Workflow status badges
- Quick stats in sidebar
- Automatic active link detection

**Usage:**
```django
{% extends 'base.html' %}

{% block title %}Your Page Title{% endblock %}

{% block content %}
    <!-- Your content here -->
{% endblock %}
```

### 2. base_nosidebar.html
Base template with only top navigation (no sidebar).

**Use for:**
- Form pages
- Detail views
- Full-width content pages
- Login/authentication pages

**Usage:**
```django
{% extends 'base_nosidebar.html' %}

{% block title %}Your Page Title{% endblock %}

{% block content %}
    <!-- Your full-width content here -->
{% endblock %}
```

## Navigation Components

### includes/topnav.html
Top navigation bar component included in all base templates.

**Features:**
- Brand logo and name
- Main navigation links (Dashboard, Actions, Risk Register, etc.)
- Workflow dropdown with status counts
- Administration dropdown (superuser only)
- User profile dropdown with logout
- Active link highlighting
- Responsive mobile menu

**Context Variables Used:**
- `user` - Current logged-in user
- `parked_count` - Count of parked risks
- `pending_count` - Count of pending risks
- `approved_count` - Count of approved risks
- `rejected_count` - Count of rejected risks

### includes/sidenav.html
Sidebar navigation component.

**Features:**
- Quick access links (Dashboard, New Risk)
- Workflow section with status badges
- Other links section
- Quick stats panel
- Active link highlighting
- Sticky positioning

**Context Variables Used:**
- `user` - Current logged-in user
- `parked_count`, `pending_count`, `approved_count`, `rejected_count`
- `total_risks` - Total number of risks
- `high_count` - Count of high-priority risks

## Available Blocks

### In All Base Templates:
- `{% block title %}` - Page title (appears in browser tab)
- `{% block content %}` - Main page content
- `{% block extra_styles %}` - Additional CSS styles
- `{% block extra_scripts %}` - Additional JavaScript

### In base.html Only:
- `{% block sidebar %}` - Override entire sidebar (rare use case)

## Active Link Detection

Navigation links automatically highlight based on the current URL name:

```django
<a class="nav-link {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}" 
   href="{% url 'dashboard' %}">
    <i class="fas fa-home me-1"></i> Dashboard
</a>
```

## Context Variables Required

For proper navigation display, views should provide these context variables:

**Essential:**
- `user` - Authenticated user (provided by @login_required decorator)

**Optional (for badge counts):**
- `parked_count` - Default: 0
- `pending_count` - Default: 0
- `approved_count` - Default: 0
- `rejected_count` - Default: 0
- `total_risks` - Default: 0
- `high_count` - Default: 0

**Note:** All counts have default values of 0, so pages will still work without providing them.

## Styling

### Global Styles
Base templates include:
- Bootstrap 5.3.0-alpha1
- Font Awesome 6.4.0
- Custom admin-style fonts (13px base)
- Card hover effects
- Form input styling

### Adding Custom Styles

```django
{% extends 'base.html' %}

{% block extra_styles %}
<style>
    .custom-class {
        /* your styles */
    }
</style>
{% endblock %}
```

## Responsive Behavior

- **Desktop (>= 992px):** Full sidebar + top nav
- **Tablet/Mobile (< 992px):** Top nav only (sidebar hidden)
- Navigation collapses to hamburger menu on mobile

## Role-Based Navigation

Some navigation items are conditional:

- **Administration dropdown** - Only visible to superusers
- **Settings link** - Only in sidebar for superusers
- **Approve/Reject actions** - Only for superusers in workflow pages

## Example: Converting Existing Templates

**Before:**
```django
<!DOCTYPE html>
<html>
<head>
    <title>My Page</title>
    <!-- All navigation code repeated -->
</head>
<body>
    <!-- Navbar code -->
    <!-- Sidebar code -->
    <!-- Content -->
</body>
</html>
```

**After:**
```django
{% extends 'base.html' %}

{% block title %}My Page - RiskMate ERP{% endblock %}

{% block content %}
    <!-- Only your page-specific content -->
{% endblock %}
```

## Best Practices

1. **Use base.html** for most pages (with sidebar)
2. **Use base_nosidebar.html** for forms and full-width layouts
3. **Always set block title** for better SEO and UX
4. **Provide context variables** from views for accurate badge counts
5. **Use breadcrumbs** for nested pages:
   ```django
   <nav aria-label="breadcrumb">
       <ol class="breadcrumb">
           <li class="breadcrumb-item"><a href="{% url 'dashboard' %}">Home</a></li>
           <li class="breadcrumb-item active">Current Page</li>
       </ol>
   </nav>
   ```

## Troubleshooting

**Sidebar not showing:**
- Check if you're using `base.html` (not `base_nosidebar.html`)
- Ensure screen width is >= 992px (sidebar hidden on mobile)

**Badge counts showing 0:**
- Add context variables to your view
- Use `|default:0` filter in templates for safety

**Active link not highlighting:**
- Ensure URL pattern has a `name` parameter
- Check that `request.resolver_match.url_name` matches your URL name

**User dropdown not working:**
- Ensure Bootstrap JS is loaded
- Check that user is authenticated

## Future Enhancements

Potential improvements:
- Add breadcrumb component
- Create notification dropdown
- Add search bar in top nav
- Create mobile-optimized sidebar
- Add theme switcher (dark mode)
