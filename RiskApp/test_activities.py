from riskregister.models import Risk, Control, Mitigation, RiskOwner

owners = RiskOwner.objects.all()
print('Checking activities per owner:\n')

for o in owners:
    risks = Risk.objects.filter(risk_owner=o, is_deleted=False).count()
    controls = Control.objects.filter(control_owner=o, is_active=True).count()
    mitigations = Mitigation.objects.filter(responsible_person=o).count()
    
    print(f"{o.name} (ID:{o.id}):")
    print(f"  Risks: {risks}")
    print(f"  Controls: {controls}")
    print(f"  Mitigations: {mitigations}")
    print()
