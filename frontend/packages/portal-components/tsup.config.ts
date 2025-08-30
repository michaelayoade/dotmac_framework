import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    'next',
    '@dotmac/ui',
    '@dotmac/primitives',
    '@dotmac/providers',
    '@dotmac/headless',
    '@dotmac/design-system',
    '@dotmac/network',
    '@dotmac/assets',
    '@dotmac/journey-orchestration'
  ],
  treeshake: true,
  splitting: false,
  sourcemap: true,
  minify: false,
});
