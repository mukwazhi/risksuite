import os
import sys

# Ensure project package is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'RiskApp'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')

import django
django.setup()

from django.conf import settings

print('EMAIL_BACKEND=', settings.EMAIL_BACKEND)
print('DEFAULT_FROM_EMAIL=', settings.DEFAULT_FROM_EMAIL)
print('ADMINS=', settings.ADMINS)
print('SITE_URL=', getattr(settings, 'SITE_URL', 'not set'))
