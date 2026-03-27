#!/usr/bin/env python
"""
Utility script to link Django User accounts to RiskOwner profiles
This helps ensure users can see their own activities on the My Activities page
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RiskApp.settings')
django.setup()

from django.contrib.auth.models import User
from riskregister.models import RiskOwner

def show_mappings():
    """Display current user-to-riskowner mappings"""
    print("=" * 80)
    print("USER TO RISK OWNER MAPPINGS")
    print("=" * 80)
    
    users = User.objects.all()
    risk_owners = RiskOwner.objects.all()
    
    print("\nCURRENT USERS:")
    print("-" * 80)
    for user in users:
        print(f"{user.id:3d}. {user.username:15s} | Email: {user.email or '(none)':30s} | Name: {user.first_name} {user.last_name}")
        
        # Try to find matching RiskOwner
        matched = None
        if user.email:
            matched = risk_owners.filter(email__iexact=user.email).first()
        if not matched and user.first_name and user.last_name:
            full_name = f"{user.first_name} {user.last_name}"
            matched = risk_owners.filter(name__iexact=full_name).first()
        
        if matched:
            print(f"     ✓ MATCHED to RiskOwner: {matched.name} ({matched.email})")
        else:
            print(f"     ✗ NO MATCH - This user won't see their activities!")
    
    print("\nAVAILABLE RISK OWNERS:")
    print("-" * 80)
    for ro in risk_owners:
        dept_abbr = ro.department.abbreviation if ro.department else 'N/A'
        print(f"{ro.id:3d}. {ro.name:20s} | Email: {ro.email or '(none)':30s} | Dept: {dept_abbr}")

def link_user_to_riskowner(user_id, riskowner_email):
    """
    Update a Django user's email to match a RiskOwner's email
    
    Args:
        user_id: ID of the Django User
        riskowner_email: Email of the RiskOwner to link to
    """
    try:
        user = User.objects.get(id=user_id)
        risk_owner = RiskOwner.objects.get(email__iexact=riskowner_email)
        
        old_email = user.email
        user.email = risk_owner.email
        user.save()
        
        print(f"✓ Successfully linked user '{user.username}' to RiskOwner '{risk_owner.name}'")
        print(f"  Changed email from '{old_email}' to '{risk_owner.email}'")
        return True
        
    except User.DoesNotExist:
        print(f"✗ Error: User with ID {user_id} not found")
        return False
    except RiskOwner.DoesNotExist:
        print(f"✗ Error: RiskOwner with email {riskowner_email} not found")
        return False

def create_riskowner_for_user(user_id, department_id=None):
    """
    Create a new RiskOwner for a Django user
    
    Args:
        user_id: ID of the Django User
        department_id: Optional ID of the department
    """
    from riskregister.models import Department
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if RiskOwner already exists
        if RiskOwner.objects.filter(email__iexact=user.email).exists():
            print(f"✗ Error: RiskOwner with email {user.email} already exists")
            return False
        
        # Get department
        department = None
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
            except Department.DoesNotExist:
                print(f"✗ Warning: Department with ID {department_id} not found, creating without department")
        
        # Create RiskOwner
        full_name = f"{user.first_name} {user.last_name}".strip()
        if not full_name:
            full_name = user.username
        
        risk_owner = RiskOwner.objects.create(
            name=full_name,
            email=user.email,
            department=department
        )
        
        print(f"✓ Successfully created RiskOwner '{risk_owner.name}' for user '{user.username}'")
        return True
        
    except User.DoesNotExist:
        print(f"✗ Error: User with ID {user_id} not found")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:
        # No arguments, just show current mappings
        show_mappings()
        print("\nUSAGE:")
        print("  Show mappings:           python link_users.py")
        print("  Link user to RiskOwner:  python link_users.py link <user_id> <riskowner_email>")
        print("  Create RiskOwner:        python link_users.py create <user_id> [department_id]")
        print("\nEXAMPLE:")
        print("  python link_users.py link 1 mra@gmail.com")
        print("  python link_users.py create 1 5")
        
    elif sys.argv[1] == 'link' and len(sys.argv) >= 4:
        user_id = int(sys.argv[2])
        riskowner_email = sys.argv[3]
        link_user_to_riskowner(user_id, riskowner_email)
        print("\nUpdated mappings:")
        show_mappings()
        
    elif sys.argv[1] == 'create' and len(sys.argv) >= 3:
        user_id = int(sys.argv[2])
        department_id = int(sys.argv[3]) if len(sys.argv) >= 4 else None
        create_riskowner_for_user(user_id, department_id)
        print("\nUpdated mappings:")
        show_mappings()
        
    else:
        print("Invalid arguments. Run without arguments for usage info.")
