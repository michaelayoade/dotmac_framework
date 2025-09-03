import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'profile/index': 'src/profile/index.ts',
    'notifications/index': 'src/notifications/index.ts',
    'security/index': 'src/security/index.ts',
    'appearance/index': 'src/appearance/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  external: ['react', 'react-dom', '@dotmac/ui'],
  splitting: false,
  treeshake: true,
  clean: true,
});
