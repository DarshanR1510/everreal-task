import { test, expect } from '@playwright/test';

test.use({ storageState: 'fixtures/agent-alpen.json' });

/**
 * WHAT THIS PROVES
 * -----------------
 * The `session` cookie carries `agencyId`, but `GET /api/contacts/:id/notes`
 * (fetched by the /contacts/[id] page) never checks the requested contact's
 * agencyId against the caller's session agencyId. Confirmed live: logged in
 * as agent@alpen-immobilien.de (agencyId "alpen-immobilien"), a request to
 * /contacts/1 (a München/EverReal contact, agencyId "everreal-demo")
 * currently returns HTTP 200 with that contact's full data and notes.
 *
 * WHO IS HARMED IF THIS REGRESSES
 * --------------------------------
 * Every agency on the platform, not just Alpen or EverReal — any
 * authenticated agent can read any other agency's client PII (names,
 * contact details, private notes) by guessing/incrementing a contact id.
 * This is horizontal privilege escalation across all tenants (OWASP
 * API1/BOLA: broken object-level authorization).
 *
 * SEVERITY REASONING
 * -------------------
 * - Victim: all non-Alpen agencies' clients (broad, multi-tenant blast radius).
 * - Blast radius: total — every contact id on the platform is reachable by
 *   every authenticated user regardless of role or tenant.
 * - Reversibility: the read itself doesn't destroy data, but a confidentiality
 *   breach can't be "undone" once the data has been read/exfiltrated.
 * High severity despite being read-only, because it defeats the entire
 * multi-tenancy boundary the product is sold on.
 *
 * WHY ASSERT FIXED BEHAVIOR, NOT CURRENT BEHAVIOR
 * -------------------------------------------------
 * Asserting today's 200-with-foreign-data response as "expected" would bake
 * the bug into the test suite as a passing contract. Instead this test
 * asserts the only acceptable outcomes — explicit denial (403/404) or a 200
 * that never contains another agency's data — so it FAILS now (proving the
 * bug) and turns green only once tenant scoping is actually enforced.
 */
test.describe('Cross-tenant contact isolation', () => {
  test('Alpen agent cannot load a non-Alpen (München/EverReal) contact via /contacts/1', async ({ page }) => {
    const notesResponse = page.waitForResponse((r) => r.url().includes('/api/contacts/1/notes'));
    await page.goto('/contacts/1');
    const resp = await notesResponse;

    if (resp.status() === 200) {
      const body = await resp.json();
      // If the endpoint returns 200 at all, the contact payload itself must
      // never belong to a foreign agency.
      // No `??` fallback here on purpose: if agencyId is missing entirely, that's a
      // malformed/empty response that must fail loudly, not be treated as "correct".
      expect(body.contact?.agencyId).toBe('alpen-immobilien');
    } else {
      expect([403, 404]).toContain(resp.status());
    }

    // Defense-in-depth: the page renders "Agency: {contact.agencyId}" directly —
    // it must never show the foreign agency's id even if some other bug leaks
    // data into the DOM despite the API being fixed.
    await expect(page.getByText(/Agency:\s*everreal-demo/i)).toHaveCount(0);
  });
});
