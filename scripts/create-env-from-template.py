#!/usr/bin/env python3
"""
Simple Python script to replace placeholders in environment templates
This avoids sed issues with special characters in secrets
"""

import sys
import os
from pathlib import Path

def replace_placeholders(template_path, output_path, replacements):
    """Replace placeholders in template file with actual values"""
    
    # Read template file
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace all placeholders
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    
    # Write output file
    with open(output_path, 'w') as f:
        f.write(content)
    
    # Set secure permissions
    os.chmod(output_path, 0o600)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: create-env-from-template.py <template_file> <output_file> <replacements_file>")
        sys.exit(1)
    
    template_file = sys.argv[1]
    output_file = sys.argv[2]
    replacements_file = sys.argv[3]
    
    # Read replacements from file (format: KEY=VALUE)
    replacements = {}
    with open(replacements_file, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                replacements[key] = value
    
    replace_placeholders(template_file, output_file, replacements)
    print(f"✅ Created {output_file} from template with secure permissions")