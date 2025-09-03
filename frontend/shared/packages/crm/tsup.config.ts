import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    customers: 'src/customers/index.ts',
    contacts: 'src/contacts/index.ts',
    leads: 'src/leads/index.ts',
    communications: 'src/communications/index.ts',
    analytics: 'src/analytics/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom'],
  sourcemap: true,
  minify: false,
  splitting: false,
});
