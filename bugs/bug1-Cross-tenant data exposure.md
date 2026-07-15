## BUG-1 — Cross-tenant data exposure (any agency can read any other agency's contacts)
**Severity: CRITICAL**

**Repro:**
1. Log in as `agent@alpen-immobilien.de` (Alpen agency).
2. In the URL bar, go to `/contacts/1` (a contact belonging to EverReal, a different agency).
3. The full contact detail loads — name, email, phone, property, internal notes.
4. Confirmed at the API level: `GET /api/contacts` returns all agencies' contacts with HTTP 200, regardless of which agency the logged-in user belongs to. No server-side agency filter.

**Expected:** An Alpen agent must only ever see Alpen contacts. Requesting another agency's contact should return 403/404 or empty — never that agency's data.

**Actual:** Any authenticated user can read every agency's contacts by changing the contact ID. Includes confidential VIP records (e.g. portfolio owners marked "confidential").

**Who is harmed, how badly, how reversible:**
- **Victim:** every agency on the platform and their clients — not just Alpen or EverReal.
- **How badly:** total loss of tenant isolation, the core guarantee the product is sold on. In production this is a GDPR-reportable data breach and likely a contract-terminating event for affected customers. Competitor agencies can harvest each other's client lists.
- **Reversibility:** none. Once data is read/exfiltrated, the confidentiality breach cannot be undone, even after a fix ships.