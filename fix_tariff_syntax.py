#!/usr/bin/env python3
"""
Fix remaining syntax errors in tariff.py
"""

import re

# Read the file
with open('isp-framework/src/dotmac_isp/sdks/services/tariff.py', 'r') as f:
    content = f.read()

# Fix all missing closing parentheses
fixes = [
    (r'Decimal\(str\(usage_amount\)(?!\))', r'Decimal(str(usage_amount))'),
    (r'Decimal\(str\(tier\["limit"\]\)(?!\))', r'Decimal(str(tier["limit"]))'),
    (r'Decimal\(str\(tier\["price"\]\)(?!\))', r'Decimal(str(tier["price"]))'),
    (r'Decimal\(str\(usage_amount\)(?!\))', r'Decimal(str(usage_amount))'),
    (r'Decimal\(str\(volume_break\["discount_rate"\]\)(?!\))', r'Decimal(str(volume_break["discount_rate"]))'),
    (r'Decimal\(str\(period\["price"\]\)(?!\))', r'Decimal(str(period["price"]))'),
    (r'Decimal\(str\(period_usage\) \* period_price\)', r'Decimal(str(period_usage)) * period_price'),
    (r'Decimal\(str\(discount_config\["value"\]\) / 100\)', r'Decimal(str(discount_config["value"])) / 100'),
    (r'Decimal\(str\(discount_config\["value"\]\)(?!\))', r'Decimal(str(discount_config["value"]))'),
    (r'list\(self\._service\._tariff_plans\.values\(\)(?!\))', r'list(self._service._tariff_plans.values())'),
]

for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content)

# Write back
with open('isp-framework/src/dotmac_isp/sdks/services/tariff.py', 'w') as f:
    f.write(content)

print("✅ Fixed syntax errors in tariff.py")