import { createTsupConfig } from '@dotmac/typescript-config/tsup.base';

export default createTsupConfig({
  entry: {
    index: 'src/index.ts',
    'data-display/index': 'src/data-display/index.ts',
    'composition/index': 'src/composition/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: false,
  external: [
    'react', 
    'react-dom', 
    '@dotmac/primitives',
    '@dotmac/registry',
    '@dotmac/security',
    '@dotmac/rbac',
    '@dotmac/monitoring/observability',
    '@tanstack/react-table',
    '@tanstack/react-virtual',
    '@tanstack/react-query',
    '@hello-pangea/dnd',
    'react-window',
    'react-window-infinite-loader',
    'clsx',
    'class-variance-authority',
    'lucide-react',
    'zod'
  ],
  // esbuild options inherited via base
});
