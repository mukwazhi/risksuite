"""
Management command to link existing RiskOwners to User accounts
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

def link_risk_owners():
    """Link existing RiskOwners to User accounts by email matching"""
    
    print("=== Risk Owner to User Linking Tool ===\n")
    
    # Get all RiskOwners without linked user accounts
    unlinked_owners = RiskOwner.objects.filter(user__isnull=True)
    
    if not unlinked_owners.exists():
        print("✓ All RiskOwners are already linked to User accounts.")
        return
    
    print(f"Found {unlinked_owners.count()} unlinked RiskOwners:")
    
    for owner in unlinked_owners:
        print(f"\n--- Processing: {owner.name} ({owner.email}) ---")
        
        # Try to find matching user by email
        matching_users = User.objects.filter(email__iexact=owner.email) if owner.email else User.objects.none()
        
        if matching_users.count() == 1:
            user = matching_users.first()
            owner.user = user
            owner.save()
            print(f"✓ Linked {owner.name} to user: {user.username} ({user.email})")
        
        elif matching_users.count() > 1:
            print(f"⚠ Multiple users found with email {owner.email}:")
            for user in matching_users:
                print(f"  - {user.username} ({user.email}) - {user.get_full_name()}")
            print("  Manual intervention required.")
        
        else:
            print(f"✗ No user found with email: {owner.email}")
            print("  Create a user account or update the email address.")
    
    print(f"\n=== Summary ===")
    linked_count = RiskOwner.objects.filter(user__isnull=False).count()
    total_count = RiskOwner.objects.count()
    print(f"Linked RiskOwners: {linked_count}/{total_count}")
    
    if linked_count < total_count:
        print("\nTo create user accounts for unlinked RiskOwners:")
        print("python create_risk_owner_users.py")

if __name__ == "__main__":
    link_risk_owners()