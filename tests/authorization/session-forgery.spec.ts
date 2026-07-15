import { test, expect } from '@playwright/test';

function decodeSession(cookieValue: string) {
  return JSON.parse(Buffer.from(decodeURIComponent(cookieValue), 'base64').toString('utf-8'));
}
function encodeSession(payload: object) {
  return encodeURIComponent(Buffer.from(JSON.stringify(payload)).toString('base64'));
}

/**
 * WHAT THIS PROVES
 * -----------------
 * The `session` cookie is `base64(JSON.stringify({email, role, agencyId, iat}))`
 * with no signature/HMAC/JWT structure at all — the server trusts whatever
 * JSON it decodes. Confirmed live: decoding the cookie, changing `agencyId`
 * or `role` (e.g. to "admin"), re-encoding, and setting it back makes the
 * server treat the request as that forged identity, including persisting
 * writes (e.g. contact notes) made under it — the `author` field on notes is
 * itself taken straight from this forgeable cookie.
 *
 * WHO IS HARMED IF THIS REGRESSES
 * --------------------------------
 * The entire platform and every tenant on it, not one agency — this is a
 * full authentication-bypass / privilege-escalation primitive. A forged
 * `role: "admin"` cookie grants global admin capability over every agency's
 * data; a forged `agencyId` grants a normal agent access to any tenant.
 *
 * SEVERITY REASONING
 * -------------------
 * - Victim: the whole platform (every agency + the EverReal operator).
 * - Blast radius: total — any resource, any action (read AND write), with no
 *   privilege ceiling once role can be forged to "admin".
 * - Reversibility: low. Writes performed under a forged identity persist and
 *   corrupt data provenance (note authorship, audit trails) in a way that
 *   can't be cleanly distinguished from legitimate activity after the fact.
 * This is the most severe of the three defects tested in this suite
 * (OWASP A01/A07 — broken access control / identification & auth failures).
 *
 * WHY ASSERT FIXED BEHAVIOR, NOT CURRENT BEHAVIOR
 * -------------------------------------------------
 * Asserting "the forged cookie works" as expected would encode the exploit
 * as a passing contract. Instead these tests assert what a signed/
 * server-validated session would produce — the tampered cookie is rejected
 * (redirect to /login, write requests return 401/403, no persisted forged
 * data) — so they FAIL now (proving the app currently accepts forgeries) and
 * pass once the app stops trusting unsigned, client-suppliable session data.
 */
test.describe('Session cookie forgery / privilege escalation', () => {
  test('tampering agencyId in the session cookie must be rejected, not silently trusted', async ({ browser }) => {
    const context = await browser.newContext({ storageState: 'fixtures/agent-alpen.json' });
    const page = await context.newPage();

    const cookies = await context.cookies();
    const session = cookies.find((c) => c.name === 'session')!;
    const decoded = decodeSession(session.value);
    expect(decoded.agencyId).toBe('alpen-immobilien'); // sanity check on starting state

    const forged = { ...decoded, agencyId: 'everreal-demo' };
    await context.addCookies([{ ...session, value: encodeSession(forged) }]);

    await page.goto('/contacts');
    // Correct behavior: a payload the server never issued (no signature match)
    // must invalidate the session outright, not grant access under the new agencyId.
    await expect(page).toHaveURL(/\/login/);

    await context.close();
  });

  test('tampering role to admin must be rejected and must not allow persisting data as a forged admin', async ({ browser }) => {
    const context = await browser.newContext({ storageState: 'fixtures/agent-everreal.json' });
    const page = await context.newPage();

    const cookies = await context.cookies();
    const session = cookies.find((c) => c.name === 'session')!;
    const decoded = decodeSession(session.value);
    expect(decoded.role).toBe('agent');

    const forged = { ...decoded, role: 'admin' };
    await context.addCookies([{ ...session, value: encodeSession(forged) }]);

    // Attempt a write under the forged admin identity.
    const writeResp = await page.request.post('/api/contacts/1/notes', {
      data: { body: 'forged-admin-note-should-not-persist' },
    });
    expect(writeResp.status(), 'forged session must not be able to write data').toBeGreaterThanOrEqual(401);
    expect(writeResp.status()).toBeLessThan(500);

    await page.goto('/contacts');
    await expect(page).toHaveURL(/\/login/);

    // Verify no persistence occurred, using a clean legitimate session.
    const cleanContext = await browser.newContext({ storageState: 'fixtures/agent-everreal.json' });
    const cleanResp = await cleanContext.request.get('/api/contacts/1/notes');
    const cleanBody = await cleanResp.json();
    expect(cleanBody.notes.some((n: any) => n.body?.includes('forged-admin-note-should-not-persist'))).toBe(false);
    await cleanContext.close();

    await context.close();
  });
});
