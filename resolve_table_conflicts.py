#!/usr/bin/env python3
"""
Script to resolve database table conflicts in the omnichannel module.
This script will:
1. Rename the conflicting models.py to models_legacy.py
2. Update all imports to use models_production.py
3. Consolidate duplicate table definitions
"""

import os
import re
from pathlib import Path

def find_imports_to_fix():
    """Find all files that import from the conflicting models."""
    files_to_fix = []
    
    # Find files importing from omnichannel.models (the conflicting one)
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for imports from the conflicting models
                        if re.search(r'from.*omnichannel\.models(?!\w)', content):
                            files_to_fix.append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return files_to_fix

def fix_imports(filepath):
    """Fix imports in a specific file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace imports from models to models_production
        original_content = content
        
        # Fix direct imports
        content = re.sub(
            r'from dotmac_isp\.modules\.omnichannel\.models(?!\w)',
            'from dotmac_isp.modules.omnichannel.models_production',
            content
        )
        
        # Fix import aliases  
        content = re.sub(
            r'from \.\.\.modules\.omnichannel\.models(?!\w)',
            'from ...modules.omnichannel.models_production',
            content
        )
        
        content = re.sub(
            r'from \.models(?!\w)',
            'from .models_production',
            content
        )
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in: {filepath}")
            return True
    
    except Exception as e:
        print(f"Error fixing imports in {filepath}: {e}")
    
    return False

def rename_conflicting_models():
    """Rename the conflicting models.py to models_legacy.py"""
    models_path = "isp-framework/src/dotmac_isp/modules/omnichannel/models.py"
    legacy_path = "isp-framework/src/dotmac_isp/modules/omnichannel/models_legacy.py"
    
    if os.path.exists(models_path):
        try:
            os.rename(models_path, legacy_path)
            print(f"Renamed {models_path} to {legacy_path}")
            
            # Create a new models.py that imports from models_production
            with open(models_path, 'w', encoding='utf-8') as f:
                f.write('''"""
Omnichannel models - imports from production models.

This file exists to maintain compatibility while we migrate to models_production.py
as the canonical model definitions.
"""

# Import all models from production to maintain compatibility
from .models_production import *

# Explicitly import commonly used models to avoid any import issues
from .models_production import (
    ContactType,
    CustomerContact,
    ContactCommunicationChannel,
    CommunicationInteraction,
    Agent,
    AgentTeam,
    RegisteredChannel,
    ChannelConfiguration,
    RoutingRule,
    InteractionStatus,
    ChannelType,
    InteractionResponse,
    InteractionEscalation,
    ConversationThread,
    AgentTeamMembership,
    AgentPerformanceMetrics,
    ChannelAnalytics,
    InteractionResponse as InteractionResponseModel,
)
''')
            print(f"Created compatibility import file at {models_path}")
            
        except Exception as e:
            print(f"Error renaming models file: {e}")

def main():
    """Main function to resolve table conflicts."""
    print("Resolving database table conflicts in omnichannel module...")
    
    # Find files that need import fixes
    files_to_fix = find_imports_to_fix()
    print(f"Found {len(files_to_fix)} files with imports to fix")
    
    # Fix imports in found files
    fixed_count = 0
    for filepath in files_to_fix:
        if fix_imports(filepath):
            fixed_count += 1
    
    print(f"Fixed imports in {fixed_count} files")
    
    # Rename conflicting models file
    rename_conflicting_models()
    
    print("Table conflict resolution completed!")
    print("\nNext steps:")
    print("1. Run database migrations to ensure table names are consistent")
    print("2. Test the application to ensure all imports work correctly")
    print("3. Consider removing models_legacy.py after thorough testing")

if __name__ == "__main__":
    main()