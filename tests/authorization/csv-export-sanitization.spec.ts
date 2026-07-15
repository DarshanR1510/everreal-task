import { test, expect } from '@playwright/test';
import fs from 'fs';

test.use({ storageState: 'fixtures/agent-everreal.json' });

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') { inQuotes = false; }
      else cur += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { cells.push(cur); cur = ''; }
    else cur += c;
  }
  cells.push(cur);
  return cells;
}

/**
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
