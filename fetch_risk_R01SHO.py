import os
import sys
# Ensure project root is on sys.path so Django settings can be imported
root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
import django
django.setup()
from django.test import Client
c = Client()
r = c.get('/risks/R01SHO/')
with open('risk_R01SHO.html','wb') as f:
    f.write(r.content)
print('STATUS', r.status_code)
print('LENGTH', len(r.content))
