from django.db.models import Count
from django.core.cache import cache


def workflow_counts(request):
    """Provide counts for parked, pending, approved, rejected risks and total risks.
    Uses a short cache TTL so the values aren't recomputed on every request but
    remain reasonably fresh.
    Safe to call during migrations/startup; returns zeros if models aren't ready.
    """
    try:
        from .models import Risk

        # Cache the computed counts for 30 seconds to avoid DB hits on every request
        cached = cache.get('workflow_counts')
        if cached:
            data = cached.copy()
        else:
            data = None

        counts = Risk.objects.values('status').annotate(n=Count('id'))
        mapping = {c['status']: c['n'] for c in counts}
        data = {
            'parked_count': mapping.get('parked', 0),
            'pending_count': mapping.get('pending', 0),
            'approved_count': mapping.get('approved', 0),
            'rejected_count': mapping.get('rejected', 0),
            'total_risks': Risk.objects.count(),
        }
        if data is None:
            counts = Risk.objects.values('status').annotate(n=Count('id'))
            mapping = {c['status']: c['n'] for c in counts}
            data = {
                'parked_count': mapping.get('parked', 0),
                'pending_count': mapping.get('pending', 0),
                'approved_count': mapping.get('approved', 0),
                'rejected_count': mapping.get('rejected', 0),
                'total_risks': Risk.objects.count(),
            }
            cache.set('workflow_counts', data, 30)

        # For anonymous users, return the counts only
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return data

        # Notifications have been removed; return counts only.
        return data
    except Exception:
        # If DB/models not ready (migrations) return safe defaults
        return {
            'parked_count': 0,
            'pending_count': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'total_risks': 0,
        }
