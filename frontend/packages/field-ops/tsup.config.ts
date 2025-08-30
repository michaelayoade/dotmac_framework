import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    'index': 'src/index.ts',
    'work-orders': 'src/work-orders/index.ts',
    'gps': 'src/gps/index.ts',
    'workflows': 'src/workflows/index.ts'
  },
  format: ['cjs', 'esm'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom'],
  sourcemap: true,
  minify: false,
  splitting: false
});
