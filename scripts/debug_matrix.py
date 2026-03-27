import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
import django
django.setup()
from riskregister.models import Risk
qs = Risk.objects.filter(is_deleted=False)
print('Risks count:', qs.count())
for r in qs[:20]:
    print(r.risk_id, 'likelihood=', r.likelihood, 'impact=', r.impact, 'score=', r.risk_score)
