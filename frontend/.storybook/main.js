/** @type {import('@storybook/nextjs').StorybookConfig} */
const config = {
  stories: [
    '../packages/*/src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../apps/*/src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../stories/**/*.stories.@(js|jsx|ts|tsx|mdx)',
  ],

  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
    '@storybook/addon-a11y',
    '@storybook/addon-docs',
    '@storybook/addon-controls',
    '@storybook/addon-viewport',
    '@storybook/addon-backgrounds',
    '@storybook/addon-measure',
    '@storybook/addon-outline',
    'storybook-addon-performance',
    '@chromatic-com/storybook',
  ],

  framework: {
    name: '@storybook/nextjs',
    options: {
      nextConfigPath: '../apps/admin/next.config.js',
    },
  },

  features: {
    experimentalRSC: true,
  },

  typescript: {
    check: false,
    reactDocgen: 'react-docgen-typescript',
    reactDocgenTypescriptOptions: {
      shouldExtractLiteralValuesFromEnum: true,
      propFilter: (prop) => (prop.parent ? !/node_modules/.test(prop.parent.fileName) : true),
    },
  },

  // Core configuration
  core: {
    disableTelemetry: true,
  },

  // Docs configuration
  docs: {
    autodocs: 'tag',
    defaultName: 'Documentation',
  },

  // Performance optimizations
  managerHead: (head) => `
    ${head}
    <meta name="theme-color" content="#000000" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  `,

  // Static directories
  staticDirs: ['../public', '../apps/admin/public'],

  // Webpack customization
  webpackFinal: async (config, { configType }) => {
    // Add support for CSS modules
    config.module.rules.push({
      test: /\.module\.css$/,
      use: [
        'style-loader',
        {
          loader: 'css-loader',
          options: {
            modules: true,
          },
        },
      ],
    });

    // Add support for TypeScript path mapping
    config.resolve.alias = {
      ...config.resolve.alias,
      '@dotmac/primitives': require('path').resolve(__dirname, '../packages/primitives/src'),
      '@dotmac/headless': require('path').resolve(__dirname, '../packages/headless/src'),
      '@dotmac/styled-components': require('path').resolve(
        __dirname,
        '../packages/styled-components/src'
      ),
      '@dotmac/registry': require('path').resolve(__dirname, '../packages/registry/src'),
      '@dotmac/security': require('path').resolve(__dirname, '../packages/security/src'),
      '@dotmac/testing': require('path').resolve(__dirname, '../packages/testing/src'),
    };

    return config;
  },

  // Vite configuration (if using Vite)
  viteFinal: async (config, { configType }) => {
    if (config.resolve) {
      config.resolve.alias = {
        ...config.resolve.alias,
        '@dotmac/primitives': require('path').resolve(__dirname, '../packages/primitives/src'),
        '@dotmac/headless': require('path').resolve(__dirname, '../packages/headless/src'),
        '@dotmac/styled-components': require('path').resolve(
          __dirname,
          '../packages/styled-components/src'
        ),
        '@dotmac/registry': require('path').resolve(__dirname, '../packages/registry/src'),
        '@dotmac/security': require('path').resolve(__dirname, '../packages/security/src'),
        '@dotmac/testing': require('path').resolve(__dirname, '../packages/testing/src'),
      };
    }

    return config;
  },
};

export default config;
