import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: [
        'src/lib/api/stage1.ts',
        'src/lib/queries/stage1.ts',
        'src/app/(dashboard)/integrations/**',
        'src/app/(dashboard)/ingestion/**',
      ],
      exclude: [
        'src/**/*.test.{ts,tsx}',
      ]
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
