import { createTsupConfig } from '@dotmac/typescript-config/tsup.base';

export default createTsupConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: false,
  external: ['react', 'react-dom'],
});
