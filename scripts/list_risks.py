import os
import sys
import django

# Ensure project package path is on sys.path (RiskApp folder)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
riskapp_path = os.path.join(project_root, 'RiskApp')
if riskapp_path not in sys.path:
	sys.path.insert(0, riskapp_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
django.setup()

from riskregister.models import Risk

qs = Risk.objects.filter(is_deleted=False).order_by('pk')[:20]
print([r.risk_id for r in qs])
