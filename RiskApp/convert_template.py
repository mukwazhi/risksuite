"""
Template Conversion Helper Script
This script helps convert RiskMate templates to use the new base template structure.

Usage:
    python convert_template.py <template_path> <base_type>
    
    base_type: 'sidebar' or 'nosidebar'
    
Example:
    python convert_template.py templates/riskregister/view_risk.html nosidebar
"""

import sys
import re
from pathlib import Path


def extract_title(content):
    """Extract title from HTML"""
    match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    if match:
        title = match.group(1)
        # Clean up common suffixes
        title = title.replace(' - RiskPad', '').replace(' - RiskMate', '').strip()
        return f"{title} - RiskMate ERP"
    return "Page - RiskMate ERP"


def extract_styles(content):
    """Extract page-specific styles"""
    styles = []
    for match in re.finditer(r'<style>(.*?)</style>', content, re.DOTALL | re.IGNORECASE):
        style_content = match.group(1).strip()
        # Filter out global styles that are in base template
        if 'font-family' not in style_content or len(style_content) > 200:
            styles.append(style_content)
    
    if styles:
        return '\n'.join(styles)
    return ''


def extract_content(content):
    """Extract main content, removing nav and common wrappers"""
    # Remove DOCTYPE, html, head, body tags
    content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<html.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<body.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
    
    # Remove navigation sections
    content = re.sub(r'<nav class="navbar.*?</nav>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove sidebar if present
    content = re.sub(r'<div class="col-lg-2.*?sidebar.*?</div>\s*</div>', '', content, flags=re.DOTALL)
    
    # Remove style tags
    content = re.sub(r'<style>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove script imports at the end
    content = re.sub(r'<script src="https://cdn\.jsdelivr\.net.*?</script>', '', content, flags=re.DOTALL)
    
    return content.strip()


def convert_template(file_path, base_type='sidebar'):
    """Convert template to use base template"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        return False
    
    print(f"Converting: {path.name}")
    
    # Read original content
    with open(path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Check if already converted
    if '{% extends' in original_content:
        print(f"  ⚠️  Template already extends a base template")
        return False
    
    # Extract components
    title = extract_title(original_content)
    styles = extract_styles(original_content)
    content = extract_content(original_content)
    
    # Build new template
    base_template = 'base.html' if base_type == 'sidebar' else 'base_nosidebar.html'
    
    new_template = f"""{{%extends '{base_template}' %}}

{{% block title %}}{title}{{% endblock %}}
"""
    
    if styles:
        new_template += f"""
{{% block extra_styles %}}
<style>
{styles}
</style>
{{% endblock %}}
"""
    
    new_template += f"""
{{% block content %}}
{content}
{{% endblock %}}
"""
    
    # Create backup
    backup_path = path.with_suffix('.html.bak')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  ✅ Backup created: {backup_path.name}")
    
    # Write converted template
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_template)
    
    print(f"  ✅ Converted to use {base_template}")
    print(f"  ℹ️  Please review and test the converted template")
    
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    template_path = sys.argv[1]
    base_type = sys.argv[2] if len(sys.argv) > 2 else 'sidebar'
    
    if base_type not in ['sidebar', 'nosidebar']:
        print(f"Error: base_type must be 'sidebar' or 'nosidebar', got '{base_type}'")
        sys.exit(1)
    
    success = convert_template(template_path, base_type)
    
    if success:
        print("\n✨ Conversion complete!")
        print("Next steps:")
        print("  1. Review the converted template")
        print("  2. Add breadcrumb navigation if needed")
        print("  3. Test the page in browser")
        print("  4. Update view to provide context variables (parked_count, etc.)")
    else:
        print("\n❌ Conversion failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
