#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
django.setup()

from django.contrib.auth.models import User
from riskregister.models import RiskOwner, Risk, Control, Mitigation

print('=== USERS ===')
for u in User.objects.all():
    print(f'{u.id}: {u.username} | email: "{u.email}" | name: "{u.first_name} {u.last_name}" | staff: {u.is_staff} | super: {u.is_superuser}')

print('\n=== RISK OWNERS ===')
for ro in RiskOwner.objects.all():
    dept_name = ro.department.name if ro.department else 'None'
    print(f'{ro.id}: {ro.name} | email: "{ro.email}" | dept: {dept_name}')
    
    risks = Risk.objects.filter(risk_owner=ro, is_deleted=False).count()
    controls = Control.objects.filter(control_owner=ro, is_active=True).count()
    mitigations = Mitigation.objects.filter(responsible_person=ro).count()
    print(f'   -> Risks: {risks}, Controls: {controls}, Mitigations: {mitigations}')
