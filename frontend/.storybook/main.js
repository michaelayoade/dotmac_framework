/** @type {import('@storybook/nextjs').StorybookConfig} */
const config = {
  stories: [
    '../packages/*/src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../isp-framework/*/src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../management-portal/*/src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../stories/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../stories/**/*.mdx',
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
    '@storybook/addon-design-tokens',
  ],

  framework: {
    name: '@storybook/nextjs',
    options: {
      nextConfigPath: '../isp-framework/admin/next.config.js',
    },
  },

  features: {
    experimentalRSC: true,
    buildStoriesJson: true,
  },

  typescript: {
    check: false,
    reactDocgen: 'react-docgen-typescript',
    reactDocgenTypescriptOptions: {
      shouldExtractLiteralValuesFromEnum: true,
      propFilter: (prop) => (prop.parent ? !/node_modules/.test(prop.parent.fileName) : true),
    },
  },

  core: {
    disableTelemetry: true,
  },

  docs: {
    autodocs: 'tag',
    defaultName: 'Documentation',
  },

  // Performance optimizations
  managerHead: (head) => `
    ${head}
    <meta name="theme-color" content="#007bff" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  `,

  staticDirs: ['../public', '../isp-framework/admin/public'],

  webpackFinal: async (config, { configType }) => {
    // Add TypeScript path mapping
    config.resolve.alias = {
      ...config.resolve.alias,
      '@dotmac/primitives': require('path').resolve(__dirname, '../packages/primitives/src'),
      '@dotmac/ui': require('path').resolve(__dirname, '../packages/ui/src'),
      '@dotmac/headless': require('path').resolve(__dirname, '../packages/headless/src'),
      '@dotmac/styled-components': require('path').resolve(
        __dirname,
        '../packages/styled-components/src'
      ),
      '@dotmac/security': require('path').resolve(__dirname, '../packages/security/src'),
      '@dotmac/testing': require('path').resolve(__dirname, '../packages/testing/src'),
    };

    // CSS modules support
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

    return config;
  },
};

export default config;
