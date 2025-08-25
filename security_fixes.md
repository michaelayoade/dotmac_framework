# Critical Security Fixes for Import Issues

## HIGH PRIORITY: Fix Security Vulnerabilities

### 1. Replace Pickle with JSON (Deserialization Security)

**Files to Fix:**
- `isp-framework/src/dotmac_isp/shared/cache.py`
- `management-platform/app/core/cache.py`

**Issue**: Pickle can execute arbitrary code during deserialization
**Fix**: Replace with JSON or use Redis native serialization

```python
# BEFORE (vulnerable):
import pickle
data = pickle.loads(cached_data)  # DANGEROUS

# AFTER (secure):
import json
data = json.loads(cached_data)    # SAFE
```

### 2. Sanitize Subprocess Calls (Command Injection)

**Files to Fix:**
- `isp-framework/src/dotmac_isp/api/plugins_endpoints.py`
- `isp-framework/src/dotmac_isp/core/ssl_manager.py`

**Issue**: Subprocess without input validation = command injection
**Fix**: Use shlex.quote() or subprocess with shell=False

```python
# BEFORE (vulnerable):
subprocess.run(f"command {user_input}")  # DANGEROUS

# AFTER (secure):
import shlex
subprocess.run(["command", shlex.quote(user_input)])  # SAFE
```

### 3. Secure XML Processing

**Files to Fix:**
- `shared/scripts/automated-remediation.py`
- `shared/scripts/quality-gate-check.py`

**Issue**: XML parsing can be exploited (XML bombs, XXE attacks)
**Fix**: Use defusedxml or validate XML input

```python
# BEFORE (vulnerable):
import xml.etree.ElementTree as ET
data = ET.parse(xml_input)  # DANGEROUS

# AFTER (secure):
from defusedxml import ElementTree as ET
data = ET.parse(xml_input)  # SAFE
```