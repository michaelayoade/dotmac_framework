import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    services: 'src/services/index.ts',
    models: 'src/models/index.ts',
    algorithms: 'src/algorithms/index.ts',
    utils: 'src/utils/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: false, // Disable DTS generation for now
  splitting: false,
  sourcemap: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    '@dotmac/analytics',
    '@dotmac/headless',
    '@dotmac/primitives',
    '@dotmac/providers',
    'ml-matrix',
    'ml-regression',
    'simple-statistics',
    'lodash',
    'date-fns'
  ],
  treeshake: true,
  minify: false,
});
