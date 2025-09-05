# Billing Service Consolidation Plan

## Summary
- Total billing service files: 19
- Files with duplicates: 16
- After consolidation: 8
- Files reduction: 8 (50.0%)
- Estimated lines saved: 684

## Consolidation Tasks

### 1. service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/service.py`
- **Lines Before**: 772
- **Estimated Lines After**: 498
- **Lines Saved**: 274
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/service.py`

### 2. calculation_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/domain/calculation_service.py`
- **Lines Before**: 361
- **Estimated Lines After**: 236
- **Lines Saved**: 124
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/domain/calculation_service.py`

### 3. tax_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/tax_service.py`
- **Lines Before**: 160
- **Estimated Lines After**: 99
- **Lines Saved**: 60
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/tax_service.py`

### 4. credit_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/credit_service.py`
- **Lines Before**: 146
- **Estimated Lines After**: 90
- **Lines Saved**: 56
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/credit_service.py`

### 5. payment_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/payment_service.py`
- **Lines Before**: 138
- **Estimated Lines After**: 85
- **Lines Saved**: 52
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/payment_service.py`

### 6. recurring_billing_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/recurring_billing_service.py`
- **Lines Before**: 138
- **Estimated Lines After**: 87
- **Lines Saved**: 50
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/recurring_billing_service.py`

### 7. subscription_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/subscription_service.py`
- **Lines Before**: 108
- **Estimated Lines After**: 69
- **Lines Saved**: 38
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/subscription_service.py`

### 8. invoice_service
- **Complexity**: MEDIUM
- **Main Implementation**: `/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/invoice_service.py`
- **Lines Before**: 82
- **Estimated Lines After**: 51
- **Lines Saved**: 30
- **Duplicates to Remove**:
  - `/home/dotmac_framework/src/dotmac_isp/modules/billing/services/invoice_service.py`

