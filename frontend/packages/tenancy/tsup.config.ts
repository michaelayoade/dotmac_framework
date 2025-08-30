import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    hooks: 'src/hooks/index.ts',
    components: 'src/components/index.ts',
    services: 'src/services/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: false, // Disable DTS generation for now
  splitting: false,
  sourcemap: true,
  clean: true,
  external: ['react', 'react-dom', '@dotmac/headless', '@dotmac/primitives', '@dotmac/providers'],
  treeshake: true,
  minify: false, // Disable minification for easier debugging
});
