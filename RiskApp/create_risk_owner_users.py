"""
Management command to create User accounts for RiskOwners
"""
import os
import sys
import django
from getpass import getpass

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
django.setup()

from django.contrib.auth.models import User
from riskregister.models import RiskOwner, NotificationPreference

def create_risk_owner_users():
    """Create User accounts for RiskOwners who don't have them"""
    
    print("=== Risk Owner User Creation Tool ===\n")
    
    # Get all RiskOwners without user accounts
    unlinked_owners = RiskOwner.objects.filter(user__isnull=True)
    
    if not unlinked_owners.exists():
        print("✓ All RiskOwners already have User accounts.")
        return
    
    print(f"Found {unlinked_owners.count()} RiskOwners without User accounts:")
    
    for owner in unlinked_owners:
        print(f"\n--- Creating user for: {owner.name} ({owner.email}) ---")
        
        if not owner.email:
            print("✗ No email address - skipping. Please add email to RiskOwner first.")
            continue
        
        # Check if email is already used
        if User.objects.filter(email__iexact=owner.email).exists():
            print(f"✗ User with email {owner.email} already exists.")
            continue
        
        # Generate username from email
        username = owner.email.split('@')[0]
        
        # Ensure username is unique
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        # Create user account
        try:
            user = User.objects.create_user(
                username=username,
                email=owner.email,
                first_name=owner.name.split()[0] if owner.name else '',
                last_name=' '.join(owner.name.split()[1:]) if len(owner.name.split()) > 1 else '',
                password='RiskOwner2026!'  # Default password - must be changed on first login
            )
            
            # Link to RiskOwner
            owner.user = user
            owner.save()

            # Ensure a NotificationPreference exists for the new user (expiry can be set later)
            try:
                NotificationPreference.objects.get_or_create(user=user)
            except Exception:
                # Non-fatal: continue even if preference creation fails
                pass
            
            print(f"✓ Created user account:")
            print(f"  Username: {username}")
            print(f"  Email: {owner.email}")
            print(f"  Password: RiskOwner2026! (must be changed)")
            print(f"  Linked to RiskOwner: {owner.name}")
            
        except Exception as e:
            print(f"✗ Error creating user: {str(e)}")
    
    print(f"\n=== Summary ===")
    linked_count = RiskOwner.objects.filter(user__isnull=False).count()
    total_count = RiskOwner.objects.count()
    print(f"RiskOwners with User accounts: {linked_count}/{total_count}")
    
    if linked_count > 0:
        print(f"\n=== Login Instructions ===")
        print("Risk owners can now log in at /login/ with:")
        print("- Username: (generated from email)")
        print("- Password: RiskOwner2026!")
        print("- They MUST change password on first login")
        print("- They will access their dashboard at /my-dashboard/")

if __name__ == "__main__":
    create_risk_owner_users()