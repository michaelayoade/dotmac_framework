import js from '@eslint/js';
import typescript from '@typescript-eslint/eslint-plugin';
import typescriptParser from '@typescript-eslint/parser';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import importPlugin from 'eslint-plugin-import';
import prettier from 'eslint-plugin-prettier';
import prettierConfig from 'eslint-config-prettier';
import security from 'eslint-plugin-security';
// Governance custom rules (flat-config plugin shim)
import enforceProviderPattern from './packages/governance/eslint-rules/enforce-provider-pattern.js';
import noDuplicateComponents from './packages/governance/eslint-rules/no-duplicate-components.js';

export default [
  js.configs.recommended,
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/.next/**',
      '**/out/**',
      '**/coverage/**',
      '**/.turbo/**',
      '**/playwright-report/**',
      '**/test-results/**',
    ],
  },
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        exports: 'writable',
        module: 'writable',
        require: 'readonly',
        global: 'writable',
        jest: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        test: 'readonly',
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
      react: react,
      'react-hooks': reactHooks,
      'jsx-a11y': jsxA11y,
      import: importPlugin,
      prettier: prettier,
      security: security,
      '@dotmac/governance': {
        rules: {
          'enforce-provider-pattern': enforceProviderPattern,
          'no-duplicate-components': noDuplicateComponents,
        },
      },
    },
    rules: {
      ...typescript.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      ...prettierConfig.rules,
      'prettier/prettier': 'error',
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react/display-name': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      'no-undef': 'off', // TypeScript handles this
      'no-unused-vars': 'off', // Using @typescript-eslint/no-unused-vars instead
      'import/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
          'newlines-between': 'always',
          alphabetize: {
            order: 'asc',
            caseInsensitive: true,
          },
        },
      ],
      'import/no-unresolved': 'off',
      'import/named': 'off',
      // Governance rules (single source of truth)
      '@dotmac/governance/no-duplicate-components': 'error',
      '@dotmac/governance/enforce-provider-pattern': 'error',

      // Security Rules - Prevent common vulnerabilities
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      'no-alert': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // Prevent dangerous patterns
      'no-caller': 'error',
      'no-extend-native': 'error',
      'no-extra-bind': 'error',
      'no-iterator': 'error',
      'no-lone-blocks': 'error',
      'no-loop-func': 'error',
      'no-multi-str': 'error',
      'no-new-object': 'error',
      'no-new-wrappers': 'error',
      'no-octal-escape': 'error',
      'no-proto': 'error',
      'no-return-assign': 'error',
      'no-self-compare': 'error',
      'no-sequences': 'error',
      'no-throw-literal': 'error',
      'no-unused-expressions': 'error',
      'no-useless-call': 'error',
      'no-useless-concat': 'error',
      'no-void': 'error',
      'no-with': 'error',

      // Security-specific React rules
      'react/no-danger': 'error',
      'react/no-danger-with-children': 'error',
      'react/jsx-no-script-url': 'error',
      'react/jsx-no-target-blank': ['error', { enforceDynamicLinks: 'always' }],

      // TypeScript security rules (disabled for non-TS files)
      '@typescript-eslint/no-implied-eval': 'off',
      '@typescript-eslint/no-misused-promises': 'off',
      '@typescript-eslint/no-floating-promises': 'off',

      // Code Complexity Rules (CRITICAL - CLAUDE.md Requirements)
      'complexity': ['error', { max: 10 }],
      'max-lines-per-function': ['error', { max: 50 }],
      'max-params': ['error', { max: 8 }],
      'max-depth': ['error', { max: 4 }],
      'max-statements': ['error', { max: 50 }],
      'max-lines': ['error', { max: 300 }],
      'max-nested-callbacks': ['error', { max: 3 }],

      // Security plugin rules
      'security/detect-object-injection': 'warn',

      // Custom security patterns
      'no-restricted-globals': [
        'error',
        {
          name: 'localStorage',
          message: 'Use secureStorage utility instead of direct localStorage access for security.'
        },
        {
          name: 'sessionStorage',
          message: 'Use secureStorage utility instead of direct sessionStorage access for security.'
        }
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: "CallExpression[callee.name='eval']",
          message: 'eval() is dangerous and should never be used.'
        },
        {
          selector: "NewExpression[callee.name='Function']",
          message: 'new Function() is dangerous and should never be used.'
        },
        {
          selector: "CallExpression[callee.property.name='innerHTML']",
          message: 'innerHTML can lead to XSS. Use textContent or a sanitization library.'
        },
        {
          selector: "CallExpression[callee.property.name='outerHTML']",
          message: 'outerHTML can lead to XSS. Use textContent or a sanitization library.'
        }
      ],
      'jsx-a11y/anchor-is-valid': [
        'error',
        {
          components: ['Link'],
          specialLink: ['hrefLeft', 'hrefRight'],
          aspects: ['invalidHref', 'preferButton'],
        },
      ],
    },
    settings: {
      react: {
        version: 'detect',
      },
      'import/resolver': {
        typescript: {
          alwaysTryTypes: true,
          project: ['./tsconfig.json', './apps/*/tsconfig.json', './packages/*/tsconfig.json'],
        },
      },
    },
  },
  {
    files: ['**/*.js', '**/*.mjs'],
    rules: {
      '@typescript-eslint/no-var-requires': 'off',
    },
  },
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // Enable TypeScript security rules for TS files only
      '@typescript-eslint/no-implied-eval': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
    },
  },
  {
    files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-floating-promises': 'off', // Allow unhandled promises in tests
    },
  },
];
