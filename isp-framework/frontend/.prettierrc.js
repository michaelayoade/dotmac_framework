/** @type {import('prettier').Config} */
module.exports = {
  // Line length (similar to black's default)
  printWidth: 88,

  // Indentation (similar to black)
  tabWidth: 2,
  useTabs: false,

  // Quotes (similar to black)
  singleQuote: true,
  quoteProps: 'as-needed',

  // Semicolons
  semi: true,

  // Trailing commas (similar to black)
  trailingComma: 'es5',

  // Brackets
  bracketSpacing: true,
  bracketSameLine: false,

  // Arrow functions
  arrowParens: 'avoid',

  // JSX
  jsxSingleQuote: true,

  // Prose formatting
  proseWrap: 'preserve',

  // HTML whitespace
  htmlWhitespaceSensitivity: 'css',

  // End of line
  endOfLine: 'lf',

  // Embedded language formatting
  embeddedLanguageFormatting: 'auto',

  // Plugin-specific settings
  plugins: [],

  overrides: [
    {
      files: '*.json',
      options: {
        printWidth: 200,
      },
    },
    {
      files: '*.md',
      options: {
        proseWrap: 'always',
        printWidth: 80,
      },
    },
  ],
};
