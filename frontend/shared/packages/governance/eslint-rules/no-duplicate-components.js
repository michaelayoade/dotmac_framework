/**
 * ESLint rule to prevent duplicate components across portals
 * Enforces use of unified @dotmac/ui components
 */

const { ESLintUtils } = require('@typescript-eslint/utils');

const createRule = ESLintUtils.RuleCreator(
  (name) => `https://docs.dotmac.com/eslint-rules/${name}`
);

// Components that should only come from @dotmac/ui
const UNIFIED_COMPONENTS = new Set([
  'Button',
  'Input',
  'Card',
  'Modal',
  'Form',
  'Table',
  'Toast',
  'Dialog',
  'Dropdown',
  'Select',
  'Checkbox',
  'RadioGroup',
  'Switch',
  'Tabs',
  'Accordion',
  'Avatar',
  'Badge',
  'Progress',
  'Skeleton',
  'Spinner',
  'Alert',
  'Tooltip',
]);

// Allowed local component prefixes (for portal-specific components)
const ALLOWED_LOCAL_PREFIXES = [
  'Portal',
  'Admin',
  'Customer',
  'Reseller',
  'Technician',
  'Management',
  'Local',
  'Custom',
];

module.exports = createRule({
  name: 'no-duplicate-components',
  meta: {
    type: 'problem',
    docs: {
      description: 'Prevent duplicate components that should use @dotmac/ui',
      recommended: 'error',
    },
    hasSuggestions: true,
    fixable: 'code',
    schema: [
      {
        type: 'object',
        properties: {
          allowedComponents: {
            type: 'array',
            items: { type: 'string' },
          },
          allowedPrefixes: {
            type: 'array',
            items: { type: 'string' },
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      duplicateComponent:
        'Component "{{componentName}}" should be imported from @dotmac/ui instead of creating a duplicate.',
      missingImport: 'Component "{{componentName}}" should be imported from @dotmac/ui.',
      suggestUnifiedImport:
        'Import {{componentName}} from @dotmac/ui with portal variant: <{{componentName}} variant="{{portal}}" />',
    },
  },

  defaultOptions: [{}],

  create(context, [options = {}]) {
    const allowedComponents = new Set(options.allowedComponents || []);
    const allowedPrefixes = options.allowedPrefixes || ALLOWED_LOCAL_PREFIXES;

    // Detect current portal from file path
    const filename = context.getFilename();
    const portal = detectPortal(filename);

    return {
      // Check component declarations
      'FunctionDeclaration, VariableDeclarator[init.type="ArrowFunctionExpression"], VariableDeclarator[init.type="FunctionExpression"]'(
        node
      ) {
        const componentName = getComponentName(node);
        if (!componentName) return;

        if (isProblematicComponent(componentName, allowedComponents, allowedPrefixes)) {
          context.report({
            node,
            messageId: 'duplicateComponent',
            data: { componentName },
            fix(fixer) {
              return generateImportFix(fixer, context, componentName, portal);
            },
          });
        }
      },

      // Check JSX usage without proper imports
      JSXElement(node) {
        const elementName = node.openingElement.name.name;

        if (UNIFIED_COMPONENTS.has(elementName) && !hasUnifiedImport(context, elementName)) {
          context.report({
            node,
            messageId: 'missingImport',
            data: { componentName: elementName },
            suggest: [
              {
                messageId: 'suggestUnifiedImport',
                data: { componentName: elementName, portal },
                fix(fixer) {
                  return generateImportFix(fixer, context, elementName, portal);
                },
              },
            ],
          });
        }
      },
    };
  },
});

/**
 * Detect portal from file path
 */
function detectPortal(filename) {
  const portals = ['admin', 'customer', 'reseller', 'technician', 'management'];

  for (const portal of portals) {
    if (filename.includes(`/apps/${portal}/`) || filename.includes(`apps/${portal}/`)) {
      return portal;
    }
  }

  return 'default';
}

/**
 * Extract component name from AST node
 */
function getComponentName(node) {
  if (node.type === 'FunctionDeclaration') {
    return node.id?.name;
  }

  if (node.type === 'VariableDeclarator') {
    return node.id?.name;
  }

  return null;
}

/**
 * Check if component is problematic (duplicate of unified component)
 */
function isProblematicComponent(componentName, allowedComponents, allowedPrefixes) {
  // Skip if explicitly allowed
  if (allowedComponents.has(componentName)) {
    return false;
  }

  // Skip if has allowed prefix
  if (allowedPrefixes.some((prefix) => componentName.startsWith(prefix))) {
    return false;
  }

  // Check if it's a unified component that should not be duplicated
  return UNIFIED_COMPONENTS.has(componentName);
}

/**
 * Check if unified import exists
 */
function hasUnifiedImport(context, componentName) {
  const sourceCode = context.getSourceCode();
  const imports = sourceCode.ast.body.filter((node) => node.type === 'ImportDeclaration');

  return imports.some((importNode) => {
    return (
      importNode.source.value === '@dotmac/ui' &&
      importNode.specifiers.some((spec) => spec.imported?.name === componentName)
    );
  });
}

/**
 * Generate fix to add unified import
 */
function generateImportFix(fixer, context, componentName, portal) {
  const sourceCode = context.getSourceCode();
  const existingImports = sourceCode.ast.body.filter((node) => node.type === 'ImportDeclaration');
  const uiImport = existingImports.find((node) => node.source.value === '@dotmac/ui');

  if (uiImport) {
    // Add to existing import
    const lastSpecifier = uiImport.specifiers[uiImport.specifiers.length - 1];
    return fixer.insertTextAfter(lastSpecifier, `, ${componentName}`);
  } else {
    // Create new import
    const firstImport = existingImports[0];
    const importStatement = `import { ${componentName} } from '@dotmac/ui';\n`;

    if (firstImport) {
      return fixer.insertTextBefore(firstImport, importStatement);
    } else {
      return fixer.insertTextBefore(sourceCode.ast.body[0], importStatement);
    }
  }
}
