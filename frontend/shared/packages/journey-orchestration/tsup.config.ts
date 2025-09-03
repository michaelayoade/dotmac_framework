import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    orchestrator: 'src/orchestrator/index.ts',
    analytics: 'src/analytics/index.ts',
    handoffs: 'src/handoffs/index.ts',
    events: 'src/events/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    '@dotmac/headless',
    '@dotmac/crm',
    '@dotmac/workflows-system',
    '@dotmac/business-logic',
    '@dotmac/billing-system',
    '@dotmac/field-ops',
    '@dotmac/support-system',
    '@dotmac/auth',
    '@dotmac/monitoring',
  ],
});
