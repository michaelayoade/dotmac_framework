# ESLint Improvements - Next Sprint Plan

Generated: 2025-08-18T19:50:38.084Z

## Current Status

### primitives

- **Total Issues**: 197 (58 errors, 139 warnings)
- **TypeScript any**: 45 issues
- **JSX Arrow Functions**: 62 issues
- **Unused Variables**: 9 issues
- **Complexity**: 6 issues
- **Other**: 75 issues

### headless

- **Total Issues**: 376 (126 errors, 250 warnings)
- **TypeScript any**: 138 issues
- **JSX Arrow Functions**: 15 issues
- **Unused Variables**: 8 issues
- **Complexity**: 11 issues
- **Other**: 204 issues

## Next Sprint Actions

### P1 - Critical (Complete First)

- [ ] Fix remaining complexity violations by refactoring large functions
- [ ] Address unused variable issues through ESLint --fix automation

### P2 - High Priority

- [ ] Replace remaining TypeScript `any` types in public APIs
- [ ] Set up CI automation for ESLint --fix on commits

### P3 - Medium Priority (Next Sprint)

- [ ] Address JSX arrow function violations
- [ ] Consider disabling or adjusting rules for test files

## Automation Recommendations

1. **CI Integration**: Add `pnpm run lint:fix` to pre-commit hooks
2. **Type Safety**: Gradually replace `any` with proper types in internal code
3. **Performance**: Address JSX arrow functions in hot code paths only

## Commands for Next Sprint

```bash
# Auto-fix what we can
pnpm run lint:fix

# Focus on public APIs first
npm run lint-improvements -- --public-apis-only

# Generate progress report
npm run lint:report
```
