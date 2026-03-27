"""
Fix Mr A's user account linking
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
django.setup()

from django.contrib.auth.models import User
from riskregister.models import RiskOwner

def fix_mr_a_linking():
    """Link Mr A's user account to RiskOwner record"""
    
    print("=== Fixing Mr A User Linking ===\n")
    
    # Find Mr A's user and risk owner records
    try:
        user = User.objects.get(username='MrA')
        print(f"Found user: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("✗ User 'MrA' not found")
        return
    
    try:
        risk_owner = RiskOwner.objects.get(name='Mr A')
        print(f"Found RiskOwner: {risk_owner.name} (ID: {risk_owner.id})")
    except RiskOwner.DoesNotExist:
        print("✗ RiskOwner 'Mr A' not found")
        return
    
    # Update user email to match risk owner
    if not user.email:
        user.email = risk_owner.email
        user.save()
        print(f"✓ Updated user email to: {user.email}")
    
    # Link the risk owner to the user
    if not risk_owner.user:
        risk_owner.user = user
        risk_owner.save()
        print(f"✓ Linked RiskOwner '{risk_owner.name}' to User '{user.username}'")
    else:
        print(f"✓ RiskOwner '{risk_owner.name}' already linked to user")
    
    print(f"\n=== Result ===")
    print(f"User '{user.username}' can now log in and access the risk owner dashboard")
    print(f"Dashboard URL: /my-dashboard/")

if __name__ == "__main__":
    fix_mr_a_linking()