import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts', 'src/components/index.ts', 'src/hooks/index.ts', 'src/utils/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    '@dotmac/headless',
    '@dotmac/ui',
    '@dotmac/primitives',
    '@dotmac/providers',
  ],
  treeshake: true,
  splitting: false,
  minify: process.env.NODE_ENV === 'production',
  sourcemap: true,
});
