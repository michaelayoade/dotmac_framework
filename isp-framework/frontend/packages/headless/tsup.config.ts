import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: false, // Skip DTS for now
  external: ['next/navigation', 'next/router', 'react', 'react-dom', '@dotmac/primitives'],
  clean: true,
  splitting: false,
  sourcemap: true,
  treeshake: true,
  skipNodeModulesBundle: true,
  esbuildOptions(options) {
    options.logLevel = 'error'; // Only show errors
  },
});
