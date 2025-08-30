import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    types: 'src/types/index.ts',
    'components/index': 'src/components/index.ts',
    'hooks/index': 'src/hooks/index.ts',
    'providers/index': 'src/providers/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: false, // TypeScript declarations disabled due to build issues
  splitting: true,
  sourcemap: true,
  clean: true,
  external: ['react', 'react-dom'],
  esbuildOptions(options) {
    options.banner = {
      js: '"use client";',
    };
  },
});
