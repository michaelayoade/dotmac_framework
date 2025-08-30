import { defineConfig } from 'tsup';

export default defineConfig([
  // Main entry point
  {
    entry: ['src/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    clean: true,
    sourcemap: true,
    treeshake: true,
    splitting: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  },
  // Workflows module
  {
    entry: ['src/workflows/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    sourcemap: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  },
  // Stepper module
  {
    entry: ['src/stepper/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    sourcemap: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  },
  // Approval module
  {
    entry: ['src/approval/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    sourcemap: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  },
  // Tracking module
  {
    entry: ['src/tracking/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    sourcemap: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  },
  // Forms module
  {
    entry: ['src/forms/index.ts'],
    format: ['cjs', 'esm'],
    dts: true,
    sourcemap: true,
    outDir: 'dist',
    outExtension: ({ format }) => ({
      js: format === 'esm' ? '.mjs' : '.js'
    }),
    external: ['react', 'react-dom']
  }
]);
