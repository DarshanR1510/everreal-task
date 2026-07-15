import { test as setup, expect } from '@playwright/test';
import path from 'path';

/**
 * storageState pattern
 * --------------------
 * Playwright can snapshot a browser context's cookies + localStorage into a
 * JSON file via `context.storageState({ path })`. Any later test that starts
 * with `test.use({ storageState: 'fixtures/<file>.json' })` (or a project-level
 * `use.storageState`) launches already logged in — no UI login step, no
 * repeated auth calls, and each account's session is isolated to its own file.
 *
 * This file performs the one real UI login per account and writes the result
 * to /fixtures. It is not a feature test — run it on its own (or wire it in
 * later as a Playwright "setup" project with `dependencies: ['setup']`) before
 * relying on the generated storageState files.
 *
 *   npx playwright test tests/auth/auth.setup.ts
 *
 * Regenerate the fixtures whenever a session expires or credentials change.
 */

const FIXTURES_DIR = path.join(__dirname, '..', '..', 'fixtures');

interface Account {
  name: string;
  storageStateFile: string;
  emailEnvVar: string;
  passwordEnvVar: string;
}

const ACCOUNTS: Account[] = [
  {
    name: 'agent-everreal',
    storageStateFile: 'agent-everreal.json',
    emailEnvVar: 'EVERREAL_AGENT_EMAIL',
    passwordEnvVar: 'EVERREAL_AGENT_PASSWORD',
  },
  {
    name: 'admin-everreal',
    storageStateFile: 'admin-everreal.json',
    emailEnvVar: 'EVERREAL_ADMIN_EMAIL',
    passwordEnvVar: 'EVERREAL_ADMIN_PASSWORD',
  },
  {
    name: 'agent-alpen',
    storageStateFile: 'agent-alpen.json',
    emailEnvVar: 'ALPEN_AGENT_EMAIL',
    passwordEnvVar: 'ALPEN_AGENT_PASSWORD',
  },
];

for (const account of ACCOUNTS) {
  setup(`authenticate as ${account.name}`, async ({ page }) => {
    const email = process.env[account.emailEnvVar];
    const password = process.env[account.passwordEnvVar];

    if (!email || !password) {
      throw new Error(
        `Missing credentials for ${account.name}. Set ${account.emailEnvVar} and ` +
          `${account.passwordEnvVar} in .env (see .env.example).`,
      );
    }

    await page.goto('/login');
    await page.locator('#email').fill(email);
    await page.locator('#password').fill(password);
    await page.getByRole('button', { name: 'Sign in' }).click();

    // Wait for the post-login redirect so the storageState captures an
    // authenticated session rather than the login page itself.
    await expect(page).not.toHaveURL(/\/login$/);

    await page.context().storageState({
      path: path.join(FIXTURES_DIR, account.storageStateFile),
    });
  });
}
