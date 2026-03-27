import os, sys, traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
import django
django.setup()
from django.test import Client

client = Client()
url = '/indicators/39/assessments/'
print('Requesting', url)
try:
    response = client.get(url)
    print('Status code:', response.status_code)
    content = response.content.decode('utf-8', errors='replace')
    print('Content snippet:')
    print(content[:2000])
except Exception as e:
    print('Exception occurred:')
    traceback.print_exc()
    sys.exit(2)
