import os, sys
sys.path.insert(0, 'RiskApp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
import django
try:
    django.setup()
    import riskregister.templatetags.risk_extras as re
    print('IMPORT_OK', re)
except Exception:
    import traceback
    traceback.print_exc()
