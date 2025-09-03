import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  minify: false,
  external: [
    'react',
    'react-dom',
    '@dotmac/primitives',
    '@dotmac/headless',
    '@dotmac/data-tables',
    '@dotmac/ui',
    'recharts',
    'framer-motion',
    'lucide-react',
    'date-fns',
    'clsx',
    'class-variance-authority',
    'jspdf',
    'jspdf-autotable',
    'xlsx',
    'html2canvas',
    'react-to-print',
  ],
  esbuildOptions(options) {
    options.jsx = 'automatic';
  },
  onSuccess: async () => {
    console.log('✅ Reporting package built successfully');
  },
});
