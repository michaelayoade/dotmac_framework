# Package Consolidation Strategy

## Current State Analysis

### Package Portfolio Overview
- **12 packages** totaling **65,623 lines of code**
- **Average maintainability: 59.6/100** (needs improvement)
- **All packages are large** (>2000 LOC) - no small packages detected
- **No obvious consolidation opportunities** due to package sizes

### Key Findings

#### 1. Dependency Overload 🚨
**All packages** have excessive external dependencies (>20), indicating:
- Potential over-engineering
- Dependency management complexity
- Security vulnerability surface area
- Maintenance overhead

#### 2. Functionality Overlap
Multiple packages share similar concerns:
- **6 packages** have tenant-related functionality
- **6 packages** include auth components  
- **5 packages** have monitoring capabilities
- **5 packages** implement API patterns

#### 3. Missing Infrastructure
- **50% lack proper testing** (dotmac-network-automation)
- **17% missing documentation** (dotmac-plugins, dotmac-secrets)
- All packages need dependency cleanup

## Strategic Consolidation Approach

### Phase 1: Dependency Cleanup (1-2 weeks)
**Before consolidation**, reduce dependency bloat:

```bash
# Audit each package's dependencies
for pkg in packages/dotmac-*; do
    echo "=== $pkg ==="
    find $pkg -name "*.py" -exec grep -h "^import\|^from" {} \; | sort | uniq -c | sort -nr
done
```

**Target**: Reduce average dependencies from >20 to <15 per package.

### Phase 2: Functional Consolidation (4-8 weeks)

#### Option A: Core Service Consolidation
```
dotmac-core-services/
├── auth/          # Merge dotmac-auth + auth components
├── tenant/        # Consolidate tenant functionality  
├── database/      # Merge database-toolkit + database
└── monitoring/    # Observability + monitoring components
```

#### Option B: Layer-Based Consolidation  
```
dotmac-infrastructure/    # Low-level: database, networking, secrets
dotmac-platform/         # Mid-level: auth, tenant, events, websockets  
dotmac-application/      # High-level: tasks, plugins, observability
```

#### Option C: Domain-Driven Consolidation
```
dotmac-identity/         # auth + tenant + secrets
dotmac-communication/    # events + websockets + tasks
dotmac-data/            # database-toolkit + database  
dotmac-platform/        # application + plugins + observability
dotmac-network/         # network-automation (standalone)
```

### Phase 3: Implementation Strategy

#### Recommended Approach: **Option C - Domain-Driven**

**Rationale**:
- Aligns with business domains
- Reduces cross-package dependencies  
- Clearer ownership boundaries
- Easier to understand and maintain

#### Implementation Steps:

1. **dotmac-identity** (High Priority)
   ```bash
   # Merge auth + tenant + secrets
   mkdir -p packages/dotmac-identity/src/dotmac/identity/
   # Consolidate: auth flows, tenant isolation, secret management
   ```
   - **Estimated effort**: 3-4 weeks
   - **Risk**: Medium (auth is critical)
   - **Benefit**: Single identity management system

2. **dotmac-communication** (Medium Priority)  
   ```bash
   # Merge events + websockets + tasks
   mkdir -p packages/dotmac-communication/src/dotmac/communication/
   # Consolidate: event handling, real-time communication, background tasks
   ```
   - **Estimated effort**: 2-3 weeks  
   - **Risk**: Low (less critical systems)
   - **Benefit**: Unified communication layer

3. **dotmac-data** (Low Priority)
   ```bash
   # Merge database-toolkit + database
   mkdir -p packages/dotmac-data/src/dotmac/data/
   # Consolidate: ORM, migrations, repositories, queries
   ```
   - **Estimated effort**: 2-3 weeks
   - **Risk**: Medium (data access is critical)
   - **Benefit**: Consistent data access patterns

4. **dotmac-platform** (Low Priority)
   ```bash  
   # Keep application + plugins + observability separate initially
   # Consider merger after other consolidations prove successful
   ```

## Migration Planning

### Pre-Consolidation Checklist
- [ ] Audit and reduce dependencies in all packages
- [ ] Add missing tests to dotmac-network-automation  
- [ ] Add documentation to dotmac-plugins and dotmac-secrets
- [ ] Create dependency mapping between packages
- [ ] Identify breaking change scope

### Consolidation Process
1. **Create new consolidated package structure**
2. **Copy code maintaining git history**  
3. **Update import paths progressively**
4. **Run comprehensive tests**
5. **Update CI/CD pipelines**
6. **Deprecate old packages gradually**

### Breaking Change Management
```python
# Example: Maintain backward compatibility
# OLD: from dotmac.auth.core import authenticate
# NEW: from dotmac.identity.auth import authenticate

# Add compatibility layer in old package
from dotmac.identity.auth import authenticate
import warnings

def old_authenticate(*args, **kwargs):
    warnings.warn("dotmac.auth.core is deprecated, use dotmac.identity.auth", 
                 DeprecationWarning, stacklevel=2)
    return authenticate(*args, **kwargs)
```

## Success Metrics

### Quantitative Goals
- **Reduce package count**: 12 → 6-8 packages
- **Improve maintainability**: 59.6 → 75+ average score
- **Reduce dependencies**: <15 average external dependencies
- **Increase test coverage**: 100% packages have tests
- **Complete documentation**: 100% packages documented

### Qualitative Goals  
- Clearer separation of concerns
- Easier onboarding for new developers
- Reduced cognitive load when working across domains
- Simplified dependency management
- Better IDE support and navigation

## Risk Mitigation

### High-Risk Areas
1. **Authentication consolidation** - Critical system changes
2. **Database layer changes** - Data consistency concerns  
3. **Import path updates** - Potential breaking changes across codebase

### Mitigation Strategies
1. **Feature flags** for new consolidated packages
2. **Parallel operation** during transition period
3. **Comprehensive testing** at each migration step
4. **Gradual rollout** starting with least critical systems
5. **Rollback plan** for each consolidation phase

## Timeline Estimate

| Phase | Duration | Effort | Priority |
|-------|----------|--------|----------|
| Dependency Cleanup | 2 weeks | Low | High |
| dotmac-communication | 3 weeks | Medium | Medium |
| dotmac-data | 3 weeks | Medium | Low |
| dotmac-identity | 4 weeks | High | High |
| dotmac-platform review | 2 weeks | Low | Low |
| **Total** | **14 weeks** | **Mixed** | - |

## Alternative: No Consolidation

### Keep Current Structure If:
- Team bandwidth is limited
- System stability is paramount
- Current package boundaries work well
- Dependencies can be cleaned up in place

### Improvement Without Consolidation:
1. **Dependency audit and cleanup** (mandatory)
2. **Add missing tests and docs** (mandatory)  
3. **Establish clear package ownership**
4. **Create cross-package integration guidelines**
5. **Implement shared standards across all packages**

## Recommendation

**Proceed with Phase 1 (Dependency Cleanup) immediately**, then evaluate:

- If dependency cleanup reveals significant cross-package coupling → **Proceed with consolidation**
- If packages become well-isolated after cleanup → **Consider keeping current structure**

**Start with dotmac-communication consolidation** as proof-of-concept before tackling critical systems like identity/auth.