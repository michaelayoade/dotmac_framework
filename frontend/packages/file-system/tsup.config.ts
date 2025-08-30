import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: false, // Disable DTS build temporarily
  splitting: false,
  sourcemap: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    '@dotmac/primitives',
    '@dotmac/headless',
    '@dotmac/ui'
  ],
  esbuildOptions(options) {
    options.jsx = 'automatic';
  },
});
