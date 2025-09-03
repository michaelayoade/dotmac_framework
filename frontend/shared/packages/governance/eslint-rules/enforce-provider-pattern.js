/**
 * ESLint rule to enforce unified provider pattern
 * Prevents custom provider compositions and enforces UniversalProviders
 */

const { ESLintUtils } = require('@typescript-eslint/utils');

const createRule = ESLintUtils.RuleCreator(
  (name) => `https://docs.dotmac.com/eslint-rules/${name}`
);

// Provider components that should not be used directly
const FORBIDDEN_DIRECT_PROVIDERS = new Set([
  'QueryClientProvider',
  'ThemeProvider',
  'AuthProvider',
  'TenantProvider',
  'NotificationProvider',
  'ErrorBoundary',
]);

// Files where direct provider usage is allowed
const ALLOWED_FILES = [
  'UniversalProviders.tsx',
  'providers/index.ts',
  'providers/UniversalProviders.tsx',
];

module.exports = createRule({
  name: 'enforce-provider-pattern',
  meta: {
    type: 'problem',
    docs: {
      description: 'Enforce use of UniversalProviders instead of custom provider compositions',
      recommended: 'error',
    },
    fixable: 'code',
    schema: [
      {
        type: 'object',
        properties: {
          allowedFiles: {
            type: 'array',
            items: { type: 'string' },
          },
          forbiddenProviders: {
            type: 'array',
            items: { type: 'string' },
          },
        },
        additionalProperties: false,
      },
    ],
    hasSuggestions: true,
    messages: {
      forbiddenProvider:
        'Direct use of {{providerName}} is forbidden. Use UniversalProviders instead.',
      nestedProviders:
        'Multiple provider nesting detected. Use UniversalProviders for standardized composition.',
      missingUniversalProvider: 'App should use UniversalProviders as the root provider.',
      suggestUniversalProvider: 'Replace provider composition with UniversalProviders',
    },
  },

  defaultOptions: [{}],

  create(context, [options = {}]) {
    const allowedFiles = [...ALLOWED_FILES, ...(options.allowedFiles || [])];
    const forbiddenProviders = new Set([
      ...FORBIDDEN_DIRECT_PROVIDERS,
      ...(options.forbiddenProviders || []),
    ]);

    const filename = context.getFilename();
    const isAllowedFile = allowedFiles.some((allowedFile) => filename.includes(allowedFile));

    // Skip check if in allowed files
    if (isAllowedFile) {
      return {};
    }

    let providerCount = 0;
    let hasUniversalProvider = false;
    const detectedProviders = [];

    return {
      // Track provider usage
      JSXElement(node) {
        const elementName = node.openingElement.name.name;

        if (elementName === 'UniversalProviders') {
          hasUniversalProvider = true;
          return;
        }

        if (forbiddenProviders.has(elementName)) {
          providerCount++;
          detectedProviders.push({
            name: elementName,
            node,
          });

          context.report({
            node,
            messageId: 'forbiddenProvider',
            data: { providerName: elementName },
            suggest: [
              {
                messageId: 'suggestUniversalProvider',
                fix(fixer) {
                  return generateUniversalProviderFix(fixer, context, detectedProviders);
                },
              },
            ],
          });
        }
      },

      // Check at end of file
      'Program:exit'() {
        // Check for provider composition pattern
        if (providerCount > 1) {
          const firstProvider = detectedProviders[0];
          if (firstProvider) {
            context.report({
              node: firstProvider.node,
              messageId: 'nestedProviders',
              suggest: [
                {
                  messageId: 'suggestUniversalProvider',
                  fix(fixer) {
                    return generateUniversalProviderFix(fixer, context, detectedProviders);
                  },
                },
              ],
            });
          }
        }

        // Check for missing UniversalProvider in app root files
        if (isAppRootFile(filename) && !hasUniversalProvider && providerCount > 0) {
          context.report({
            node: context.getSourceCode().ast,
            messageId: 'missingUniversalProvider',
          });
        }
      },
    };
  },
});

/**
 * Check if file is an app root file
 */
function isAppRootFile(filename) {
  return (
    filename.includes('app/providers.tsx') ||
    filename.includes('app/layout.tsx') ||
    filename.includes('pages/_app.tsx')
  );
}

/**
 * Generate fix to replace provider composition with UniversalProviders
 */
function generateUniversalProviderFix(fixer, context, providers) {
  if (providers.length === 0) return null;

  const sourceCode = context.getSourceCode();
  const portal = detectPortalFromPath(context.getFilename());

  // Find the outermost provider
  const outermostProvider = findOutermostProvider(providers);
  const innermostProvider = findInnermostProvider(providers);

  if (!outermostProvider || !innermostProvider) return null;

  // Extract children from innermost provider
  const children = innermostProvider.node.children;
  const childrenText = children.map((child) => sourceCode.getText(child)).join('');

  // Generate UniversalProviders replacement
  const universalProviderText = `<UniversalProviders portal="${portal}">
  ${childrenText}
</UniversalProviders>`;

  // Add import if needed
  const fixes = [];

  if (!hasUniversalProviderImport(sourceCode)) {
    const firstImport = sourceCode.ast.body.find((node) => node.type === 'ImportDeclaration');
    if (firstImport) {
      fixes.push(
        fixer.insertTextBefore(
          firstImport,
          "import { UniversalProviders } from '@dotmac/providers';\n"
        )
      );
    }
  }

  // Replace provider composition
  fixes.push(fixer.replaceText(outermostProvider.node, universalProviderText));

  return fixes;
}

/**
 * Find outermost provider in nesting
 */
function findOutermostProvider(providers) {
  // For now, return first provider
  // This could be enhanced with AST traversal
  return providers[0];
}

/**
 * Find innermost provider in nesting
 */
function findInnermostProvider(providers) {
  // For now, return last provider
  // This could be enhanced with AST traversal
  return providers[providers.length - 1];
}

/**
 * Check if UniversalProviders import exists
 */
function hasUniversalProviderImport(sourceCode) {
  const imports = sourceCode.ast.body.filter((node) => node.type === 'ImportDeclaration');

  return imports.some((importNode) => {
    return (
      importNode.source.value === '@dotmac/providers' &&
      importNode.specifiers.some((spec) => spec.imported?.name === 'UniversalProviders')
    );
  });
}

/**
 * Detect portal from file path
 */
function detectPortalFromPath(filename) {
  const portals = ['admin', 'customer', 'reseller', 'technician', 'management'];

  for (const portal of portals) {
    if (filename.includes(`/apps/${portal}/`) || filename.includes(`apps/${portal}/`)) {
      return portal;
    }
  }

  return 'admin'; // default fallback
}
