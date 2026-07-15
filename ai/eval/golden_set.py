"""
golden_set.py — hand-labeled examples used to validate the judge itself.

test snippets that YOU have manually reviewed and labeled "GOOD" or "BAD",
with your own reasoning. Do not let the judge, or any AI, choose these
labels — the entire point of meta_eval.py is to check the judge's verdict
against a label you committed to independently. If the labels themselves
come from an LLM, the meta-eval proves nothing.
"""

from typing import TypedDict


class GoldenItem(TypedDict):
    name: str
    code: str
    human_label: str  # "GOOD" | "BAD" — TODO(you): replace the "TODO" placeholders
    reason: str  # TODO(you): why you labeled it that way


GOLDEN_SET = [
    {
        "name": "cross_tenant_with_fallback",
        "code": "expect(body.contact?.agencyId ?? 'alpen-immobilien').toBe('alpen-immobilien');",
        "human_label": "BAD",
        "reason": "The `?? 'alpen-immobilien'` fallback makes the test pass "
                  "when agencyId is absent from the response — it substitutes "
                  "the correct value and asserts it against itself. False "
                  "green: passes even on a malformed/empty body.",
    },
    {
        "name": "cross_tenant_fixed",
        "code": ("""
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
                 """
),
        "human_label": "GOOD",
        "reason": "Asserts the correct fixed behavior, fails loudly if "
                  "agencyId is missing, and would only pass once tenant "
                  "scoping is enforced server-side.",
    },
    {
        "name": "cross_tenant_asserts_buggy_200",
        "code": (
            "await page.goto('/contacts/1');\n"
            "const resp = await page.waitForResponse(r => r.url().includes('/api/contacts/1'));\n"
            "// asserts the CURRENT buggy behavior as 'expected'\n"
            "expect(resp.status()).toBe(200);\n"
            "const body = await resp.json();\n"
            "expect(body.contact.agencyId).toBe('everreal-demo'); // foreign data, accepted as pass\n"
        ),
        "human_label": "BAD",
        "reason": "Asserts the current buggy behavior (200 with foreign "
                  "agency data) as expected. Would go green forever and "
                  "protect the vulnerability instead of catching it.",
    },
    {
        "name": "csv_parses_file",
        "code": (
            """
**
 * WHAT THIS PROVES
 * -----------------
 * The contacts "Export CSV" link (<a href="/api/export?...">Export CSV</a>
 * on /contacts) writes contact fields into the CSV verbatim. Confirmed live:
 * contact id 6 has a seeded name of "=HYPERLINK(...)" (a formula-injection
 * payload), and the current export preserves it unescaped — opening the file
 * in Excel/Sheets executes it as a live formula rather than displaying it as
 * inert text.
 *
 * WHO IS HARMED IF THIS REGRESSES
 * --------------------------------
 * Any agent or admin who exports contacts and opens the file locally — a
 * client-supplied contact field becomes arbitrary formula execution (or
 * worse, in older Excel, DDE/OS command execution) in the exporting user's
 * spreadsheet application. This is CSV/formula injection (OWASP-adjacent
 * client-side code execution via a trusted data export).
 *
 * SEVERITY REASONING
 * -------------------
 * - Victim: the internal staff member who opens the export, not the tenant
 *   whose data was exported.
 * - Blast radius: limited to whoever opens the file, but formulas can chain
 *   to other cells/external references, so a single export can affect more
 *   than the row that carried the payload.
 * - Reversibility: poor — already-downloaded CSVs remain dangerous even
 *   after a server-side fix ships, since the fix doesn't retroactively
 *   sanitize files already on disk. This is a "stop the bleeding" bug: every
 *   day it's unfixed, more exports are one open-in-Excel away from executing
 *   attacker-controlled formulas.
 *
 * WHY ASSERT FIXED BEHAVIOR, NOT CURRENT BEHAVIOR
 * -------------------------------------------------
 * Asserting the raw formula as "expected" in the export would encode the
 * injection vector as a passing contract. Instead this test asserts the
 * neutralized form a correct sanitizer produces (leading =/+/-/@ stripped,
 * escaped, or prefixed so it can't be evaluated as a formula) — so it FAILS
 * now (raw payload passes through) and passes once export sanitization is added.
 */
test.describe('CSV export formula-injection sanitization', () => {
  test('a contact name starting with = @ + - is neutralized in the exported CSV, not a live formula', async ({ page }) => {
    // Fetch the payload live rather than hardcoding it, so the test tracks
    // whatever value actually lives in the app today.
    const contactsResp = await page.request.get('/api/contacts');
    const contactsBody = await contactsResp.json();
    const contacts = Array.isArray(contactsBody) ? contactsBody : contactsBody.contacts;
    const target = contacts.find((c: any) => /^[=+\-@]/.test(c.name));
    expect(target, 'expected a seeded contact with a formula-injection payload as its name').toBeTruthy();

    await page.goto('/contacts');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('link', { name: 'Export CSV' }).click(),
    ]);
    const csvPath = await download.path();
    const csv = fs.readFileSync(csvPath!, 'utf-8');

    const lines = csv.split(/\r?\n/).filter(Boolean);
    const header = parseCsvLine(lines[0]).map((h) => h.trim().toLowerCase());
    const nameCol = header.indexOf('name');
    const idCol = header.indexOf('id');
    expect(nameCol, 'expected a "name" column in the export').toBeGreaterThanOrEqual(0);
    expect(idCol, 'expected an "id" column in the export').toBeGreaterThanOrEqual(0);

    const row = lines.slice(1).map(parseCsvLine).find((cells) => cells[idCol] === String(target.id));
    expect(row, 'expected the target contact to appear in the export').toBeTruthy();

    const exportedName = row![nameCol];
    // Correct behavior: leading =/+/-/@ must be neutralized (e.g. prefixed
    // with a `'`) so spreadsheet software never evaluates it as a formula.
    expect(/^[=+\-@]/.test(exportedName)).toBe(false);
  });
});

"""
            
            ),
        "human_label": "GOOD",
        "reason": "Downloads and parses the actual CSV, locates the target "
                  "row, and asserts the exported cell is not a live formula — "
                  "verifies the real artifact, not a UI proxy.",
    },
    {
        "name": "csv_checks_ui_toast_only",
        "code": (
            "await page.getByRole('link', { name: 'Export CSV' }).click();\n"
            "// only checks a UI signal, never downloads or parses the CSV\n"
            "await expect(page.getByText('Export started')).toBeVisible();"
        ),
        "human_label": "BAD",
        "reason": "Never opens or parses the exported file — asserts a UI "
                  "element only. A green result here proves nothing about "
                  "whether the injection payload was neutralized.",
    },
    {
        "name": "views_subset_accepts_empty",
        "code": (
            "const full = await getAllContacts(page);\n"
            "await page.goto('/views');\n"
            "const viewed = await getViewContacts(page);\n"
            "// passes even if `viewed` is empty — empty set is a subset of everything\n"
            "expect(viewed.every(c => full.some(f => f.id === c.id))).toBe(true);"
        ),
        "human_label": "BAD",
        "reason": "A subset assertion that also accepts an empty result set "
                  "passes when the view returns zero contacts — a different "
                  "bug masquerading as a pass. Must assert neither-full-nor-empty.",
    },
    {
        "name": "views_subset_guarded",
        "code": (
            
            """

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

"""
        ),
        "human_label": "GOOD",
        "reason": "Asserts the returned set is a proper subset AND non-empty, "
                  "closing the empty-set false-pass hole.",
    },
    {
        "name": "session_forgery_rejected",
        "code": (
            
            """

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
"""
        ),
        "human_label": "GOOD",
        "reason": "Tampers the unsigned cookie and asserts the app rejects it "
                  "(redirect to login / 401-403 / no persisted forged write) — "
                  "asserts correct behavior so it fails against the current "
                  "forgeable-session build.",
    },
]