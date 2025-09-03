# @dotmac/governance

Architectural governance tools for DotMac Frontend. Provides ESLint rules, migration tools, and analysis utilities to enforce and maintain architectural standards.

## Features

- **ESLint Rules**: Prevent duplicate components and enforce provider patterns
- **Migration Tools**: Automate migration from duplicates to unified architecture
- **Analysis Tools**: Comprehensive architectural analysis and recommendations
- **CLI Tools**: Easy-to-use command-line interface

## Installation

```bash
# Install in your workspace root
pnpm add -D @dotmac/governance

# Or install globally
npm install -g @dotmac/governance
```

## CLI Tools

### Migration Tool

```bash
# Interactive migration wizard
dotmac-migrate

# Migrate components only
dotmac-migrate --mode components

# Full migration (components + providers + cleanup)
dotmac-migrate --mode full

# Analysis only (no changes)
dotmac-migrate --mode analyze
```

### Linting Tool

```bash
# Interactive linting
dotmac-lint

# Lint components only
dotmac-lint --mode components

# Full architectural lint
dotmac-lint --mode full

# Setup governance rules in projects
dotmac-lint --mode setup
```

### Analysis Tool

```bash
# Interactive analysis
dotmac-analyze

# Complete architectural analysis
dotmac-analyze --mode architecture

# Bundle impact analysis
dotmac-analyze --mode bundle

# Get recommendations
dotmac-analyze --mode recommendations
```

## ESLint Rules

### no-duplicate-components

Prevents duplicate components that should use `@dotmac/ui`.

```json
{
  "rules": {
    "@dotmac/governance/no-duplicate-components": "error"
  }
}
```

### enforce-provider-pattern

Enforces use of `UniversalProviders` instead of custom provider compositions.

```json
{
  "rules": {
    "@dotmac/governance/enforce-provider-pattern": "error"
  }
}
```

## Configuration

### ESLint Configuration

```json
{
  "plugins": ["@dotmac/governance"],
  "rules": {
    "@dotmac/governance/no-duplicate-components": [
      "error",
      {
        "allowedComponents": ["CustomButton"],
        "allowedPrefixes": ["Portal", "Admin", "Custom"]
      }
    ],
    "@dotmac/governance/enforce-provider-pattern": [
      "error",
      {
        "allowedFiles": ["UniversalProviders.tsx"],
        "forbiddenProviders": ["CustomProvider"]
      }
    ]
  }
}
```

### Programmatic Usage

```typescript
import { analyzeArchitecture, migrateComponents, lintComponents } from '@dotmac/governance';

// Analyze architecture
const analysis = await analyzeArchitecture('./frontend');

// Migrate components
const result = await migrateComponents('./frontend');

// Lint components
await lintComponents('./frontend');
```

## Migration Process

### 1. Analysis Phase

```bash
dotmac-analyze --mode architecture
```

This analyzes your current architecture and identifies:

- Duplicate components
- Inconsistent provider patterns
- Dependency conflicts
- Reusability and consistency scores

### 2. Migration Phase

```bash
dotmac-migrate --mode full
```

This migrates your codebase to use:

- Unified components from `@dotmac/ui`
- `UniversalProviders` pattern
- Consistent dependency versions

### 3. Governance Phase

```bash
dotmac-lint --mode setup
```

This sets up governance rules to prevent regressions:

- Installs ESLint rules
- Configures pre-commit hooks
- Sets up CI/CD checks

## What Gets Migrated

### Components

Before:

```tsx
// isp-framework/admin/src/components/Button.tsx
export function Button({ children, ...props }) {
  return (
    <button className='admin-button' {...props}>
      {children}
    </button>
  );
}
```

After:

```tsx
// Use unified component
export { Button } from '@dotmac/ui';

// Or with portal-specific styling
import { Button } from '@dotmac/ui';

export function AdminButton(props) {
  return <Button variant='admin' {...props} />;
}
```

### Providers

Before:

```tsx
export function Providers({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={adminTheme}>
        <AuthProvider>
          <TenantProvider>
            <NotificationProvider>{children}</NotificationProvider>
          </TenantProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

After:

```tsx
import { UniversalProviders } from '@dotmac/providers';

export function Providers({ children }) {
  return (
    <UniversalProviders
      portal='admin'
      features={{
        notifications: true,
        realtime: false,
        analytics: true,
      }}
    >
      {children}
    </UniversalProviders>
  );
}
```

## Reports

The tools generate detailed reports:

- `architecture-analysis.json` - Complete architectural analysis
- `governance-report.json` - Linting results and rule violations
- `migration-report.json` - Migration results and changes made

## Best Practices

1. **Run analysis first** to understand current state
2. **Test thoroughly** after migration
3. **Setup governance rules** to prevent regressions
4. **Review reports** to track improvements
5. **Use in CI/CD** for continuous enforcement

## Troubleshooting

### Migration Issues

- Ensure all dependencies are installed
- Check for syntax errors before migration
- Review generated code manually
- Test functionality after migration

### ESLint Issues

- Verify plugin is installed correctly
- Check configuration syntax
- Ensure rules are enabled
- Review file ignore patterns

### Performance

- Use `.eslintignore` for large files
- Configure appropriate file patterns
- Run incrementally for large codebases

## Contributing

See the main repository contributing guidelines.

## License

MIT
