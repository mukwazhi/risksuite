from django import template

register = template.Library()


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@register.filter
def risk_level_label(value):
    """Return a human label for a numeric or textual risk rating."""
    i = _to_int(value)
    if i is None:
        # assume descriptive string
        return str(value).title()
    if i >= 20:
        return 'Critical'
    if i >= 15:
        return 'High'
    if i >= 8:
        return 'Medium'
    return 'Low'


@register.filter
def risk_badge(value):
    """Return a bootstrap badge class for a risk value."""
    label = risk_level_label(value)
    if label in ('Critical', 'High'):
        return 'bg-danger'
    if label == 'Medium':
        return 'bg-warning text-dark'
    return 'bg-success'


@register.filter
def risk_border(value):
    """Return a bootstrap border class for a risk value."""
    label = risk_level_label(value)
    if label in ('Critical', 'High'):
        return 'border-danger'
    if label == 'Medium':
        return 'border-warning'
    return 'border-success'


@register.filter
def risk_text(value):
    """Return a bootstrap text color class for a risk value."""
    label = risk_level_label(value)
    if label in ('Critical', 'High'):
        return 'text-danger'
    if label == 'Medium':
        return 'text-warning'
    return 'text-success'


@register.filter
def rating_color(value):
    """Return a short bootstrap color name (danger, warning, success) for use in `bg-{{ val }}`."""
    label = risk_level_label(value)
    if label in ('Critical', 'High'):
        return 'danger'
    if label == 'Medium':
        return 'warning'
    return 'success'
