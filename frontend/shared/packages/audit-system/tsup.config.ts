import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: false, // Disable DTS generation to avoid TypeScript project issues
  clean: true,
  external: ['react', 'react-dom', '@dotmac/primitives', '@dotmac/headless', '@dotmac/ui'],
  banner: {
    js: '"use client";',
  },
});
