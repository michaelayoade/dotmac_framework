import { defineConfig } from 'tsup';

export default defineConfig({
  entry: [
    'src/index.ts',
    'src/offline/index.ts',
    'src/components/index.ts',
    'src/pwa/index.ts',
    'src/camera/index.ts',
  ],
  format: ['cjs', 'esm'],
  dts: false, // Skip DTS generation to avoid TypeScript project issues
  clean: true,
  external: ['react', 'react-dom'],
  treeshake: true,
  splitting: false,
  sourcemap: true,
  minify: false,
});
