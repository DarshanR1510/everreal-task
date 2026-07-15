import { test, expect } from '@playwright/test';

test.use({ storageState: 'fixtures/admin-everreal.json' });

function idsOf(body: any): number[] {
  const contacts = Array.isArray(body) ? body : body.contacts;
  return contacts.map((c: any) => c.id);
}

/**
 * WHAT THIS PROVES
 * -----------------
 * Saved views (/views) are meant to open a filtered subset of contacts —
 * e.g. the "München prospects" view links to /contacts?q=prospect to show
 * only `prospect`-type contacts. Confirmed live: clicking "Open" on that
 * view navigates to /contacts?q=prospect, but the page renders/returns the
 * full, unfiltered contact list — the `q` filter is silently ignored.
 *
 * WHO IS HARMED IF THIS REGRESSES
 * --------------------------------
 * Agents/admins who rely on a saved view to scope their work to a subset
 * (e.g. only prospects, or only a specific segment) — an ignored filter
 * silently re-exposes every contact, including ones the view was meant to
 * exclude, and can mislead a user into thinking they're looking at a safe,
 * filtered subset when they aren't.
 *
 * SEVERITY REASONING
 * -------------------
 * - Victim: agents/admins using saved views to scope their work.
 * - Blast radius: narrower than the other three defects in this suite — the
 *   same underlying data is already reachable elsewhere; this bug defeats a
 *   convenience/scoping control rather than a tenant or role security
 *   boundary.
 * - Reversibility: read-only, no persisted damage, but the exposure repeats
 *   every time the view is used and can cause a user to act on the wrong
 *   assumption about what they're looking at.
 *
 * WHY ASSERT FIXED BEHAVIOR, NOT CURRENT BEHAVIOR
 * -------------------------------------------------
 * Asserting "the view shows everything" as expected would encode the ignored
 * filter as a passing contract. Instead this test asserts what a working
 * filter produces — a non-empty, strict subset of the full contact list —
 * so it FAILS now (the view returns the full list) and passes once the
 * saved view's `q` filter is actually applied.
 */
test.describe('Saved view filter enforcement', () => {
  test('opening the "München prospects" saved view shows a filtered subset, not the full contact list', async ({ page }) => {
    const fullResp = await page.request.get('/api/contacts');
    const fullIds = new Set(idsOf(await fullResp.json()));

    await page.goto('/views');
    const viewResponse = page.waitForResponse((r) => r.url().includes('/api/contacts'));
    await page.getByRole('row', { name: /München prospects/ }).getByRole('link', { name: 'Open' }).click();
    await expect(page).toHaveURL(/\/contacts\?q=prospect/);
    const viewIds = idsOf(await (await viewResponse).json());

    expect(viewIds.length, 'view must not be empty').toBeGreaterThan(0);
    expect(viewIds.length, 'view must be a strict subset of the full list, not equal to it').toBeLessThan(fullIds.size);
    expect(viewIds.every((id) => fullIds.has(id)), 'every contact shown must come from the full list').toBe(true);
  });
});
