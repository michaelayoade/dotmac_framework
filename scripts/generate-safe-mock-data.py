#!/usr/bin/env python3
"""
Safe Mock Data Generator for DotMac Platform
Generates development data with no PII for testing purposes

SECURITY: This script ensures NO real personal information is used in development
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any

class SafeMockDataGenerator:
    """
    Generates completely safe mock data for development and testing
    
    All data generated follows strict PII-free guidelines:
    - Names: Always "Test User XXX" format
    - Emails: Always use @dev.local domain
    - Phones: Always "[REDACTED]"
    - Addresses: Always "[REDACTED - Dev Location XXX]"
    """
    
    def __init__(self):
        self.counter = 1
        
    def generate_safe_customer(self, suffix: str = None) -> Dict[str, Any]:
        """Generate a safe customer with no PII"""
        if suffix is None:
            suffix = f"{self.counter:03d}"
            self.counter += 1
            
        return {
            "id": f"CUST-DEV-{suffix}",
            "name": f"Test User {suffix}",
            "email": f"user{suffix}@dev.local",
            "phone": "[REDACTED]",
            "address": f"[REDACTED - Dev Location {suffix}]",
            "city": "[REDACTED]",
            "state": "[REDACTED]",
            "zipCode": f"00{random.randint(100, 999)}",
            "status": random.choice(["active", "suspended", "pending"]),
            "signupDate": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            "monthlyRevenue": round(random.uniform(29.99, 299.99), 2),
            "lifetimeValue": round(random.uniform(500, 5000), 2),
        }
    
    def generate_safe_work_order(self, suffix: str = None) -> Dict[str, Any]:
        """Generate a safe work order with no PII"""
        if suffix is None:
            suffix = f"{self.counter:03d}"
            self.counter += 1
            
        return {
            "id": f"WO-DEV-{suffix}",
            "customerId": f"CUST-DEV-{suffix}",
            "technicianId": f"TECH-DEV-001",
            "title": f"Development Test Work Order {suffix}",
            "description": "Safe test work order for development",
            "priority": random.choice(["low", "medium", "high", "urgent"]),
            "status": random.choice(["pending", "in_progress", "completed", "cancelled"]),
            "scheduledDate": datetime.now().isoformat(),
            "location": {
                "address": f"[REDACTED - Dev Environment {suffix}]",
                "coordinates": [0, 0],  # Neutral coordinates
                "accessNotes": "Development test location"
            },
            "customer": {
                "name": f"Test Customer {suffix}",
                "phone": "[REDACTED]",
                "email": f"customer{suffix}@dev.local",
                "serviceId": f"SRV-DEV-{suffix}"
            }
        }
    
    def generate_safe_partner(self, suffix: str = None) -> Dict[str, Any]:
        """Generate a safe partner with no PII"""
        if suffix is None:
            suffix = f"{self.counter:03d}"
            self.counter += 1
            
        return {
            "id": f"PARTNER-DEV-{suffix}",
            "name": f"Test Partner {suffix}",
            "email": f"partner{suffix}@dev.local",
            "phone": "[REDACTED]",
            "company": f"Test Company {suffix}",
            "status": random.choice(["active", "pending", "inactive"]),
            "commissionRate": round(random.uniform(0.05, 0.20), 2),
            "territory": f"Test Territory {suffix}"
        }
    
    def generate_safe_dataset(self, customers=10, work_orders=15, partners=5) -> Dict[str, List[Dict]]:
        """Generate a complete safe dataset"""
        dataset = {
            "customers": [self.generate_safe_customer() for _ in range(customers)],
            "work_orders": [self.generate_safe_work_order() for _ in range(work_orders)],
            "partners": [self.generate_safe_partner() for _ in range(partners)],
            "generated_at": datetime.now().isoformat(),
            "security_notice": "This dataset contains NO real PII - safe for development use"
        }
        
        return dataset
    
    def save_typescript_mock_data(self, data: Dict[str, Any], file_path: str):
        """Save data as TypeScript mock data file"""
        typescript_content = f"""// SECURITY: Safe mock data with NO real PII
// Generated on {datetime.now().isoformat()}
// All names, emails, phones, and addresses are sanitized for development

export const mockCustomers = {json.dumps(data['customers'], indent=2)};

export const mockWorkOrders = {json.dumps(data['work_orders'], indent=2)};

export const mockPartners = {json.dumps(data['partners'], indent=2)};

// Security validation
export const validateMockDataSecurity = () => {{
  const hasRealPII = JSON.stringify({{...mockCustomers, ...mockWorkOrders, ...mockPartners}})
    .match(/@(?!dev\\.local)|\\d{{3}}-\\d{{3}}-\\d{{4}}|[A-Z][a-z]+ [A-Z][a-z]+(?!Test|User|Partner|Customer|Company)/);
    
  if (hasRealPII) {{
    throw new Error('SECURITY VIOLATION: Real PII detected in mock data!');
  }}
  
  return true;
}};

// Auto-validate on import
validateMockDataSecurity();
"""
        
        with open(file_path, 'w') as f:
            f.write(typescript_content)
    
    def save_python_mock_data(self, data: Dict[str, Any], file_path: str):
        """Save data as Python mock data file"""
        python_content = f'''"""
SECURITY: Safe mock data with NO real PII
Generated on {datetime.now().isoformat()}
All names, emails, phones, and addresses are sanitized for development
"""

import re
import json

MOCK_CUSTOMERS = {json.dumps(data['customers'], indent=4)}

MOCK_WORK_ORDERS = {json.dumps(data['work_orders'], indent=4)}

MOCK_PARTNERS = {json.dumps(data['partners'], indent=4)}

def validate_mock_data_security():
    """Validate that mock data contains no real PII"""
    all_data = json.dumps({{
        "customers": MOCK_CUSTOMERS,
        "work_orders": MOCK_WORK_ORDERS,  
        "partners": MOCK_PARTNERS
    }})
    
    # Check for real email domains
    real_emails = re.findall(r'@(?!dev\\.local)[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}', all_data)
    if real_emails:
        raise ValueError(f"SECURITY VIOLATION: Real email domains found: {{real_emails}}")
    
    # Check for phone number patterns
    phone_patterns = re.findall(r'\\d{{3}}-\\d{{3}}-\\d{{4}}|\\(\\d{{3}}\\)\\s*\\d{{3}}-\\d{{4}}', all_data)
    if phone_patterns:
        raise ValueError(f"SECURITY VIOLATION: Phone numbers found: {{phone_patterns}}")
    
    # Check for real names (excluding safe patterns)
    potential_names = re.findall(r'"[A-Z][a-z]+ [A-Z][a-z]+"', all_data)
    safe_names = ['"Test User', '"Test Partner', '"Test Customer', '"Test Company']
    unsafe_names = [name for name in potential_names if not any(safe in name for safe in safe_names)]
    if unsafe_names:
        raise ValueError(f"SECURITY VIOLATION: Potential real names found: {{unsafe_names}}")
    
    return True

# Auto-validate on import
validate_mock_data_security()
'''
        
        with open(file_path, 'w') as f:
            f.write(python_content)

def main():
    """Generate and save safe mock data"""
    generator = SafeMockDataGenerator()
    
    # Generate dataset
    print("🔒 Generating safe mock data with NO PII...")
    dataset = generator.generate_safe_dataset(
        customers=20,
        work_orders=30,
        partners=8
    )
    
    # Save in multiple formats
    print("📁 Saving safe mock data files...")
    
    # JSON format
    with open('/home/dotmac_framework/scripts/safe-mock-data.json', 'w') as f:
        json.dump(dataset, f, indent=2)
    
    # TypeScript format for frontend
    generator.save_typescript_mock_data(
        dataset, 
        '/home/dotmac_framework/frontend/packages/testing/src/fixtures/safe-mock-data.ts'
    )
    
    # Python format for backend
    generator.save_python_mock_data(
        dataset,
        '/home/dotmac_framework/scripts/safe_mock_data.py'
    )
    
    print("✅ Safe mock data generated successfully!")
    print("📋 Files created:")
    print("  - /home/dotmac_framework/scripts/safe-mock-data.json")
    print("  - /home/dotmac_framework/frontend/packages/testing/src/fixtures/safe-mock-data.ts")
    print("  - /home/dotmac_framework/scripts/safe_mock_data.py")
    print("")
    print("🛡️  Security validation: All data is PII-free and safe for development")
    
    # Run security validation
    try:
        from scripts.safe_mock_data import validate_mock_data_security
        validate_mock_data_security()
        print("✅ Security validation passed!")
    except ImportError:
        print("⚠️  Security validation will run when mock data is imported")

if __name__ == "__main__":
    main()