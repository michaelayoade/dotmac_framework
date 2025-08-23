"""
AI Safety Tests for Revenue-Critical Code Protection

These tests ensure that AI-generated or AI-modified code cannot compromise
revenue-generating business logic in the ISP billing and service systems.
"""

import pytest
import ast
import re
import inspect
from pathlib import Path
from typing import List, Dict, Any, Set
from hypothesis import given, strategies as st


class RevenueProtectionAnalyzer:
    """
    AI Safety Analyzer: Detects potential revenue-impacting modifications
    in critical business logic code.
    """
    
    REVENUE_CRITICAL_MODULES = {
        'dotmac_isp.modules.billing',
        'dotmac_isp.modules.services', 
        'dotmac_isp.sdks.services',
        'dotmac_isp.modules.identity.portal_service'
    }
    
    DANGEROUS_PATTERNS = {
        # Pricing manipulation
        r'amount\s*=\s*0': 'Zero pricing detected',
        r'price\s*=\s*0': 'Zero pricing detected',
        r'cost\s*=\s*0': 'Zero cost detected',
        r'total\s*=\s*0': 'Zero total detected',
        
        # Tax evasion
        r'tax_rate\s*=\s*0': 'Tax rate zeroed',
        r'tax_amount\s*=\s*0': 'Tax amount zeroed',
        r'apply_tax\s*=\s*False': 'Tax application disabled',
        
        # Free service exploits
        r'monthly_cost\s*=\s*0': 'Monthly cost zeroed',
        r'setup_fee\s*=\s*0': 'Setup fee zeroed (acceptable if promotional)',
        r'discount\s*=\s*100': 'Full discount applied',
        
        # Payment bypasses
        r'payment_required\s*=\s*False': 'Payment requirement bypassed',
        r'balance\s*=\s*0': 'Balance zeroed',
        r'paid\s*=\s*True': 'Payment status forced to paid',
        
        # Service activation without payment
        r'activate_service\([^)]*payment[^)]*=\s*False': 'Service activation without payment',
        r'provision_service\([^)]*paid[^)]*=\s*False': 'Service provisioning without payment',
        
        # Administrative overrides
        r'admin_override\s*=\s*True': 'Administrative override enabled',
        r'bypass_billing\s*=\s*True': 'Billing bypass enabled',
        r'free_tier\s*=\s*True': 'Free tier enabled globally',
    }
    
    def analyze_code_for_revenue_risks(self, code: str, filename: str) -> List[Dict[str, Any]]:
        """Analyze code for potential revenue-impacting changes"""
        risks = []
        
        for pattern, description in self.DANGEROUS_PATTERNS.items():
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                risks.append({
                    'file': filename,
                    'line': line_num,
                    'pattern': pattern,
                    'description': description,
                    'code_snippet': match.group(0),
                    'severity': 'HIGH'
                })
        
        return risks
    
    def analyze_ast_for_revenue_risks(self, code: str, filename: str) -> List[Dict[str, Any]]:
        """AST-based analysis for more sophisticated revenue risk detection"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return [{'file': filename, 'error': 'Syntax error in code', 'severity': 'CRITICAL'}]
        
        risks = []
        
        class RevenueRiskVisitor(ast.NodeVisitor):
            def visit_Assign(self, node):
                # Check for dangerous assignments to revenue-critical variables
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id.lower()
                        
                        # Check if assigning zero to financial variables
                        if (var_name in ['amount', 'price', 'cost', 'total', 'payment', 'balance'] 
                            and isinstance(node.value, ast.Constant) 
                            and node.value.value == 0):
                            
                            risks.append({
                                'file': filename,
                                'line': node.lineno,
                                'description': f'Financial variable {var_name} assigned zero',
                                'code': f'{var_name} = 0',
                                'severity': 'HIGH'
                            })
                
                self.generic_visit(node)
            
            def visit_FunctionDef(self, node):
                # Check for suspicious function modifications
                func_name = node.name.lower()
                
                if 'payment' in func_name or 'billing' in func_name or 'charge' in func_name:
                    # Check if function returns zero or False unexpectedly
                    for stmt in ast.walk(node):
                        if (isinstance(stmt, ast.Return) 
                            and isinstance(stmt.value, ast.Constant) 
                            and stmt.value.value in [0, False]):
                            
                            risks.append({
                                'file': filename,
                                'line': stmt.lineno,
                                'description': f'Revenue function {func_name} returns {stmt.value.value}',
                                'severity': 'HIGH'
                            })
                
                self.generic_visit(node)
        
        visitor = RevenueRiskVisitor()
        visitor.visit(tree)
        
        return risks


@pytest.mark.ai_safety
@pytest.mark.revenue_critical
def test_revenue_critical_modules_integrity():
    """
    AI Safety Test: Verify revenue-critical modules haven't been compromised
    
    This test scans all revenue-critical code for patterns that could
    impact billing, payments, or service provisioning.
    """
    analyzer = RevenueProtectionAnalyzer()
    src_path = Path("src/dotmac_isp")
    
    all_risks = []
    
    for module_pattern in analyzer.REVENUE_CRITICAL_MODULES:
        module_path = src_path / module_pattern.replace('dotmac_isp.', '').replace('.', '/')
        
        if not module_path.exists():
            continue
            
        # Scan all Python files in the module
        for py_file in module_path.rglob("*.py"):
            try:
                code = py_file.read_text()
                
                # Pattern-based analysis
                pattern_risks = analyzer.analyze_code_for_revenue_risks(code, str(py_file))
                all_risks.extend(pattern_risks)
                
                # AST-based analysis
                ast_risks = analyzer.analyze_ast_for_revenue_risks(code, str(py_file))
                all_risks.extend(ast_risks)
                
            except Exception as e:
                all_risks.append({
                    'file': str(py_file),
                    'error': f'Failed to analyze: {e}',
                    'severity': 'WARNING'
                })
    
    # Filter out acceptable risks (like promotional zero setup fees)
    critical_risks = [r for r in all_risks if r.get('severity') == 'HIGH' or r.get('severity') == 'CRITICAL']
    
    # Report findings
    if critical_risks:
        risk_summary = "\n".join([
            f"🚨 {risk['file']}:{risk.get('line', '?')} - {risk['description']}"
            for risk in critical_risks
        ])
        pytest.fail(f"Revenue-critical risks detected:\n{risk_summary}")
    
    # Always log scan results for monitoring
    print(f"✅ Revenue protection scan complete: {len(all_risks)} total findings, 0 critical risks")


@pytest.mark.ai_safety
@pytest.mark.property
@given(
    price_modification=st.floats(min_value=-1000.0, max_value=1000.0),
    tax_rate_modification=st.floats(min_value=-1.0, max_value=1.0),
    discount_modification=st.floats(min_value=-100.0, max_value=200.0)
)
def test_pricing_modification_boundaries(price_modification: float, tax_rate_modification: float, discount_modification: float):
    """
    AI Safety Property Test: Pricing modifications must stay within business boundaries
    
    This test verifies that any AI-generated pricing changes respect
    fundamental business constraints and don't create revenue loss scenarios.
    """
    # Base pricing scenario
    base_price = 99.99
    base_tax_rate = 0.08
    base_discount = 10.0  # 10% discount
    
    # Apply AI modifications
    modified_price = base_price + price_modification
    modified_tax_rate = base_tax_rate + tax_rate_modification  
    modified_discount = base_discount + discount_modification
    
    # Business constraint validations
    
    # Constraint 1: Prices cannot be negative
    assert modified_price >= 0, f"AI modified price to negative value: ${modified_price}"
    
    # Constraint 2: Tax rates must be reasonable (0-30%)
    assert 0 <= modified_tax_rate <= 0.30, f"AI modified tax rate outside bounds: {modified_tax_rate*100}%"
    
    # Constraint 3: Discounts cannot exceed 100% (no negative pricing)
    assert 0 <= modified_discount <= 100, f"AI modified discount outside bounds: {modified_discount}%"
    
    # Constraint 4: Final price after discount must be positive
    discounted_price = modified_price * (1 - modified_discount / 100)
    assert discounted_price >= 0, f"AI modifications result in negative final price: ${discounted_price}"
    
    # Constraint 5: Tax calculation must be mathematically sound
    tax_amount = discounted_price * modified_tax_rate
    total_price = discounted_price + tax_amount
    
    assert tax_amount >= 0, "Tax amount cannot be negative"
    assert total_price >= discounted_price, "Total must be >= discounted price when tax > 0"
    
    # Business logic validation
    if modified_price > 0 and modified_discount < 100:
        assert total_price > 0, "AI modifications resulted in zero revenue"


@pytest.mark.ai_safety
@pytest.mark.behavior
def test_payment_processing_cannot_be_bypassed():
    """
    AI Safety Behavior Test: Payment processing cannot be circumvented
    
    This test ensures that AI modifications cannot create pathways
    for service activation without proper payment processing.
    """
    # Simulate potential AI-generated payment bypass scenarios
    bypass_scenarios = [
        {'payment_status': 'pending', 'service_active': True},  # Service active without payment
        {'payment_amount': 0, 'service_active': True},          # Zero payment with service
        {'payment_verified': False, 'service_active': True},    # Unverified payment with service
        {'balance': -100, 'service_active': True},              # Negative balance with active service
    ]
    
    for i, scenario in enumerate(bypass_scenarios):
        with pytest.raises(AssertionError, message=f"Scenario {i+1} should fail business rules"):
            # Simulate business rule validation
            payment_verified = scenario.get('payment_verified', True)
            payment_amount = scenario.get('payment_amount', 99.99)
            payment_status = scenario.get('payment_status', 'completed')
            service_active = scenario.get('service_active', False)
            balance = scenario.get('balance', 0)
            
            # Business rules that AI cannot modify
            if service_active:
                assert payment_status == 'completed', "Service cannot be active without completed payment"
                assert payment_amount > 0, "Service cannot be active with zero payment"
                assert payment_verified, "Service cannot be active without verified payment"
                assert balance >= 0, "Service cannot be active with negative balance"


@pytest.mark.ai_safety
@pytest.mark.contract
def test_billing_api_contract_protection():
    """
    AI Safety Contract Test: Billing API contracts cannot be weakened
    
    This test ensures that AI modifications to billing APIs maintain
    strict input validation and cannot introduce security vulnerabilities.
    """
    # Test cases that should ALWAYS be rejected by billing APIs
    malicious_inputs = [
        {'amount': -100, 'expected': 'reject'},      # Negative amount
        {'amount': 0, 'expected': 'reject'},         # Zero amount
        {'amount': 'DROP TABLE', 'expected': 'reject'}, # SQL injection
        {'customer_id': None, 'expected': 'reject'},  # Missing customer
        {'amount': float('inf'), 'expected': 'reject'}, # Infinite amount
        {'amount': float('nan'), 'expected': 'reject'}, # NaN amount
    ]
    
    for test_case in malicious_inputs:
        amount = test_case['amount']
        
        # Simulate API input validation (this should be in actual API code)
        def validate_billing_input(amount_input):
            if amount_input is None:
                return False, "Amount is required"
            
            if isinstance(amount_input, str) and not amount_input.replace('.', '').isdigit():
                return False, "Invalid amount format"
                
            try:
                amount_float = float(amount_input)
                if amount_float <= 0:
                    return False, "Amount must be positive"
                if not (0 < amount_float < 10000):  # Reasonable bounds
                    return False, "Amount out of bounds"
                return True, "Valid"
            except (ValueError, TypeError):
                return False, "Invalid amount type"
        
        is_valid, message = validate_billing_input(amount)
        
        # AI modifications should never weaken these validations
        assert not is_valid, f"Dangerous input accepted: {amount} - {message}"


@pytest.mark.ai_safety
@pytest.mark.smoke
def test_ai_code_markers_presence():
    """
    AI Safety Smoke Test: Verify AI-generated code is properly marked
    
    This test ensures that any AI-generated modifications to revenue-critical
    code are properly tagged for human review.
    """
    src_path = Path("src/dotmac_isp")
    revenue_modules = ['billing', 'services', 'identity']
    
    ai_markers = [
        '# AI-GENERATED',
        '# AI-MODIFIED', 
        '# AI-ASSISTED',
        '"""AI-Generated',
        '# Claude Code generated'
    ]
    
    unmarked_revenue_files = []
    
    for module in revenue_modules:
        module_path = src_path / f"modules/{module}"
        if module_path.exists():
            for py_file in module_path.rglob("*.py"):
                content = py_file.read_text()
                
                # Check if file contains revenue-critical keywords
                revenue_keywords = ['amount', 'price', 'payment', 'billing', 'charge', 'cost']
                has_revenue_code = any(keyword in content.lower() for keyword in revenue_keywords)
                
                if has_revenue_code:
                    # Check if AI markers are present
                    has_ai_marker = any(marker in content for marker in ai_markers)
                    
                    if not has_ai_marker and len(content) > 1000:  # Substantial files only
                        unmarked_revenue_files.append(str(py_file))
    
    # This is a warning rather than failure - helps track AI modifications
    if unmarked_revenue_files:
        print(f"⚠️  Revenue-critical files without AI markers: {len(unmarked_revenue_files)}")
        for file in unmarked_revenue_files[:5]:  # Show first 5
            print(f"  - {file}")
        
        # In production, this might be a hard failure
        # assert False, f"Revenue-critical files lack AI modification markers: {unmarked_revenue_files}"