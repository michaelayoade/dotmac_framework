"""
Comprehensive tests for Partner API endpoints
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch

from app.main import app
from app.database import get_db
from app.models.partner import Partner, PartnerCustomer, Commission
from app.core.commission import CommissionCalculator
from app.core.territory import TerritoryValidator

client = TestClient(app)

# Test fixtures
@pytest.fixture
def db_session():
    """Mock database session"""
    return Mock(spec=Session)

@pytest.fixture
def mock_partner():
    """Mock partner data"""
    return Partner(
        id="test-partner-123",
        company_name="Test Partner Inc",
        partner_code="TEST001",
        contact_name="John Doe",
        contact_email="john@testpartner.com",
        contact_phone="+1-555-0123",
        territory="Test Territory",
        tier="gold",
        status="active",
        monthly_customer_target=25,
        monthly_revenue_target=50000.0,
        total_lifetime_revenue=200000.0,
        created_at=datetime.utcnow()
    )

@pytest.fixture
def mock_customers():
    """Mock customer data"""
    return [
        PartnerCustomer(
            id="customer-1",
            partner_id="test-partner-123",
            name="Acme Corp",
            email="admin@acme.com",
            phone="+1-555-1234",
            address="123 Business Ave, Tech City, TC 12345",
            service_plan="enterprise",
            mrr=299.99,
            status="active",
            created_at=datetime.utcnow() - timedelta(days=30),
            contract_length=24
        ),
        PartnerCustomer(
            id="customer-2", 
            partner_id="test-partner-123",
            name="Local Cafe",
            email="owner@localcafe.com",
            phone="+1-555-5678",
            address="456 Main St, Downtown, DT 54321",
            service_plan="business_pro",
            mrr=79.99,
            status="active",
            created_at=datetime.utcnow() - timedelta(days=15),
            contract_length=12
        )
    ]

class TestPartnerDashboard:
    """Test partner dashboard endpoints"""
    
    @patch('app.api.v1.partners.dashboard.get_current_partner')
    @patch('app.api.v1.partners.dashboard.get_db')
    def test_get_dashboard_success(self, mock_get_db, mock_get_current_partner, mock_partner, mock_customers, db_session):
        """Test successful dashboard data retrieval"""
        
        # Setup mocks
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock database queries
        db_session.query.return_value.filter.return_value.first.return_value = mock_partner
        db_session.query.return_value.filter.return_value.count.return_value = len(mock_customers)
        db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = len([c for c in mock_customers if c.status == "active"])
        db_session.query.return_value.filter.return_value.with_entities.return_value.scalar.return_value = 15000.0
        db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_customers
        
        # Make request
        response = client.get("/api/v1/partners/test-partner-123/dashboard")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["partner"]["id"] == "test-partner-123"
        assert data["partner"]["name"] == "Test Partner Inc"
        assert data["partner"]["partner_code"] == "TEST001"
        assert data["partner"]["tier"] == "gold"
        
        assert "performance" in data
        assert "recent_customers" in data
        assert "sales_goals" in data
        
        # Verify performance metrics structure
        performance = data["performance"]
        assert "customers_total" in performance
        assert "customers_active" in performance
        assert "revenue" in performance
        assert "commissions" in performance
        assert "targets" in performance
    
    @patch('app.api.v1.partners.dashboard.get_current_partner')
    def test_get_dashboard_access_denied(self, mock_get_current_partner, mock_partner):
        """Test dashboard access denied for wrong partner"""
        
        # Setup mock for different partner
        different_partner = mock_partner.copy()
        different_partner.id = "different-partner"
        mock_get_current_partner.return_value = different_partner
        
        response = client.get("/api/v1/partners/test-partner-123/dashboard")
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
    
    @patch('app.api.v1.partners.dashboard.get_current_partner')
    @patch('app.api.v1.partners.dashboard.get_db')
    def test_get_dashboard_partner_not_found(self, mock_get_db, mock_get_current_partner, mock_partner, db_session):
        """Test dashboard when partner not found in database"""
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock partner not found
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/api/v1/partners/test-partner-123/dashboard")
        
        assert response.status_code == 404
        assert "Partner not found" in response.json()["detail"]


class TestPartnerCustomers:
    """Test partner customer management endpoints"""
    
    @patch('app.api.v1.partners.customers.get_current_partner')
    @patch('app.api.v1.partners.customers.get_db')
    def test_get_customers_success(self, mock_get_db, mock_get_current_partner, mock_partner, mock_customers, db_session):
        """Test successful customer list retrieval"""
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_customers)
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_customers
        db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/partners/test-partner-123/customers?page=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "customers" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert len(data["customers"]) == len(mock_customers)
        
        # Verify customer data structure
        customer = data["customers"][0]
        assert "id" in customer
        assert "name" in customer
        assert "email" in customer
        assert "status" in customer
        assert "mrr" in customer
    
    @patch('app.api.v1.partners.customers.get_current_partner')
    @patch('app.api.v1.partners.customers.get_db')
    def test_get_customers_with_filters(self, mock_get_db, mock_get_current_partner, mock_partner, mock_customers, db_session):
        """Test customer list with search and status filters"""
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock filtered results
        filtered_customers = [c for c in mock_customers if c.status == "active"]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(filtered_customers)
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = filtered_customers
        db_session.query.return_value = mock_query
        
        response = client.get("/api/v1/partners/test-partner-123/customers?search=acme&status=active")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have applied filters
        assert len(data["customers"]) <= len(mock_customers)
    
    @patch('app.api.v1.partners.customers.get_current_partner')
    @patch('app.api.v1.partners.customers.get_db')
    @patch('app.api.v1.partners.customers.validate_customer_data')
    @patch('app.api.v1.partners.customers.TerritoryValidator')
    def test_create_customer_success(self, mock_territory_validator, mock_validate, mock_get_db, mock_get_current_partner, mock_partner, db_session):
        """Test successful customer creation"""
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock validation success
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        mock_validate.return_value = mock_validation_result
        
        # Mock territory validation
        mock_territory_result = Mock()
        mock_territory_result.is_valid = True
        mock_territory_result.assigned_partner_id = mock_partner.id
        
        mock_validator_instance = Mock()
        mock_validator_instance.validate_address.return_value = mock_territory_result
        mock_territory_validator.return_value = mock_validator_instance
        
        # Mock no existing customer
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock successful creation
        new_customer = PartnerCustomer(
            id="new-customer",
            partner_id=mock_partner.id,
            name="New Customer",
            email="new@customer.com",
            phone="+1-555-9999",
            address="789 New St, Newtown, NT 99999",
            service_plan="business_pro",
            mrr=99.99,
            status="pending"
        )
        db_session.add.return_value = None
        db_session.commit.return_value = None
        db_session.refresh.return_value = None
        
        customer_data = {
            "name": "New Customer",
            "email": "new@customer.com", 
            "phone": "+1-555-9999",
            "address": "789 New St, Newtown, NT 99999",
            "plan": "business_pro",
            "mrr": 99.99
        }
        
        response = client.post("/api/v1/partners/test-partner-123/customers", json=customer_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Customer"
        assert data["email"] == "new@customer.com"
        assert data["status"] == "pending"
    
    @patch('app.api.v1.partners.customers.get_current_partner')
    @patch('app.api.v1.partners.customers.get_db')
    def test_create_customer_duplicate_email(self, mock_get_db, mock_get_current_partner, mock_partner, mock_customers, db_session):
        """Test customer creation with duplicate email"""
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Mock existing customer found
        db_session.query.return_value.filter.return_value.first.return_value = mock_customers[0]
        
        customer_data = {
            "name": "Duplicate Customer",
            "email": "admin@acme.com",  # Same email as existing customer
            "phone": "+1-555-9999",
            "address": "789 New St, Newtown, NT 99999",
            "plan": "business_pro",
            "mrr": 99.99
        }
        
        response = client.post("/api/v1/partners/test-partner-123/customers", json=customer_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestCommissionCalculation:
    """Test commission calculation engine"""
    
    def test_commission_calculator_basic(self, mock_partner, mock_customers):
        """Test basic commission calculation"""
        
        calculator = CommissionCalculator()
        customer = mock_customers[0]  # Enterprise customer with $299.99 MRR
        
        result = calculator.calculate_customer_commission(
            customer, mock_partner, is_new_customer=True
        )
        
        assert result.customer_id == customer.id
        assert result.partner_id == mock_partner.id
        assert result.total_commission > 0
        assert result.effective_rate > 0
        assert result.tier == "Gold Partner"  # Partner has gold tier
        
        # Should have new customer bonus
        assert result.breakdown["new_customer_bonus"] > 0
        
        # Should have contract length bonus for 24-month contract
        assert result.breakdown["contract_length_bonus"] > 0
        
        # Verify audit trail
        assert len(result.audit_trail) > 0
        assert any("Starting commission calculation" in entry for entry in result.audit_trail)
    
    def test_commission_calculator_tier_validation(self, mock_partner, mock_customers):
        """Test tier eligibility validation"""
        
        calculator = CommissionCalculator()
        customer = mock_customers[0]
        
        # Set partner lifetime revenue below gold tier minimum
        mock_partner.total_lifetime_revenue = 50000.0  # Below $150k gold minimum
        mock_partner.tier = "gold"  # But tier is set to gold
        
        with pytest.raises(ValueError) as exc_info:
            calculator.calculate_customer_commission(customer, mock_partner)
        
        assert "not eligible" in str(exc_info.value)
        assert "Gold Partner" in str(exc_info.value)
    
    def test_commission_calculator_security_limits(self, mock_partner, mock_customers):
        """Test commission rate security limits"""
        
        calculator = CommissionCalculator()
        customer = mock_customers[0]
        
        # Create custom tier with very high rates to trigger security check
        high_rate_tier = calculator.DEFAULT_TIERS[0].copy()
        high_rate_tier.base_rate = 0.6  # 60% rate should trigger security limit
        
        calculator.tiers = {"bronze": high_rate_tier}
        mock_partner.tier = "bronze"
        
        with pytest.raises(ValueError) as exc_info:
            calculator.calculate_customer_commission(customer, mock_partner)
        
        assert "exceeds maximum allowed" in str(exc_info.value)
    
    def test_commission_calculator_product_multipliers(self, mock_partner, mock_customers):
        """Test product-specific commission multipliers"""
        
        calculator = CommissionCalculator()
        
        # Test enterprise customer (should have 2.5x multiplier for gold tier)
        enterprise_customer = mock_customers[0]  # Enterprise plan
        result_enterprise = calculator.calculate_customer_commission(enterprise_customer, mock_partner)
        
        # Test business customer (should have 1.8x multiplier for gold tier) 
        business_customer = mock_customers[1]  # Business pro plan
        result_business = calculator.calculate_customer_commission(business_customer, mock_partner)
        
        # Enterprise should have higher multiplier effect
        assert result_enterprise.breakdown["product_multiplier"] > result_business.breakdown["product_multiplier"]
    
    def test_determine_eligible_tier(self):
        """Test tier eligibility determination"""
        
        calculator = CommissionCalculator()
        
        # Test different revenue levels
        bronze_tier = calculator.determine_eligible_tier(10000)
        assert bronze_tier.id == "bronze"
        
        silver_tier = calculator.determine_eligible_tier(75000)
        assert silver_tier.id == "silver"
        
        gold_tier = calculator.determine_eligible_tier(200000)
        assert gold_tier.id == "gold"
        
        platinum_tier = calculator.determine_eligible_tier(750000)
        assert platinum_tier.id == "platinum"


class TestIntegrationSecurity:
    """Test security aspects of API integration"""
    
    def test_authentication_required(self):
        """Test that authentication is required for all endpoints"""
        
        # Test without authentication
        response = client.get("/api/v1/partners/test-partner/dashboard")
        assert response.status_code in [401, 403]  # Should require authentication
    
    def test_partner_isolation(self):
        """Test that partners can only access their own data"""
        # This would require more complex setup with real auth
        pass
    
    def test_input_validation(self):
        """Test input validation on API endpoints"""
        
        # Test invalid customer data
        invalid_customer_data = {
            "name": "",  # Empty name should be invalid
            "email": "invalid-email",  # Invalid email format
            "phone": "123",  # Invalid phone
            "mrr": -100  # Negative MRR should be invalid
        }
        
        response = client.post("/api/v1/partners/test-partner/customers", json=invalid_customer_data)
        assert response.status_code == 422  # Validation error
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        
        # Test with malicious search term
        malicious_search = "'; DROP TABLE partners; --"
        response = client.get(f"/api/v1/partners/test-partner/customers?search={malicious_search}")
        
        # Should not cause internal server error (would indicate SQL injection vulnerability)
        assert response.status_code != 500
    
    def test_xss_protection(self):
        """Test XSS protection in inputs"""
        
        xss_payload = "<script>alert('xss')</script>"
        customer_data = {
            "name": xss_payload,
            "email": "test@example.com",
            "phone": "+1-555-0123",
            "address": "123 Test St",
            "plan": "business_pro",
            "mrr": 99.99
        }
        
        # The API should sanitize or reject XSS attempts
        response = client.post("/api/v1/partners/test-partner/customers", json=customer_data)
        # Response should either reject the data or sanitize it
        assert response.status_code in [422, 400]  # Should be validation error


class TestPerformance:
    """Test performance aspects"""
    
    @patch('app.api.v1.partners.dashboard.get_current_partner')
    @patch('app.api.v1.partners.dashboard.get_db') 
    def test_dashboard_response_time(self, mock_get_db, mock_get_current_partner, mock_partner, mock_customers, db_session):
        """Test dashboard response time under load"""
        
        import time
        
        mock_get_current_partner.return_value = mock_partner
        mock_get_db.return_value = db_session
        
        # Setup mocks for database queries
        db_session.query.return_value.filter.return_value.first.return_value = mock_partner
        db_session.query.return_value.filter.return_value.count.return_value = 1000  # Large number
        db_session.query.return_value.filter.return_value.with_entities.return_value.scalar.return_value = 50000.0
        db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_customers
        
        start_time = time.time()
        response = client.get("/api/v1/partners/test-partner-123/dashboard")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Response should be under 2 seconds even with large dataset
        response_time = end_time - start_time
        assert response_time < 2.0, f"Dashboard response took {response_time:.2f}s, should be under 2s"
    
    def test_pagination_efficiency(self):
        """Test that pagination limits result set size"""
        
        # Test with small limit
        response = client.get("/api/v1/partners/test-partner/customers?limit=5")
        # Should limit results regardless of total count
        
        # Test with maximum limit
        response = client.get("/api/v1/partners/test-partner/customers?limit=1000")  
        # Should cap at reasonable maximum (100 in our API)
        assert response.status_code in [422, 400]  # Should reject excessive limit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])