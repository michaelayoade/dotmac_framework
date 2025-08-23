import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom', 'next/dynamic', 'next'],
  treeshake: true,
  splitting: true,
  minify: true,
});
