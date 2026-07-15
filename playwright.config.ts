import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

dotenv.config();

export const BASE_URL = process.env.BASE_URL ?? 'https://qa-darshan.vercel.app';

export default defineConfig({
  testDir: './tests',
  // Include auth.setup.ts (login/storageState capture) alongside regular *.spec.ts files.
  testMatch: /.*\.(spec|setup)\.ts/,
  fullyParallel: true,
  retries: 1,
  reporter: [['html', { open: 'never' }]],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Chromium only — this is a time-boxed QA task, cross-browser coverage isn't the goal.
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
