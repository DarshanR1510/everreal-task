## BUG-2 — Forgeable session cookie (any user can become admin or any agency)
**Severity: CRITICAL**

**Repro:**
1. Log in as any account (e.g. `agent@alpen-immobilien.de`).
2. Open DevTools → Application → Cookies. The `session` cookie is plain base64, not a signed token.
3. Decode it — it's plain JSON: `{email, role, agencyId, iat}`.
4. Change `role` to `admin` (or `agencyId` to another agency like `everreal-demo`), re-encode to base64, and set it back as the cookie.
5. Reload. The server trusts the forged identity — you are now acting as that role/agency. Confirmed a forged write persists: posting a note under a forged admin identity returns 201 and saves.

**Expected:** The session must be cryptographically signed (e.g. a signed JWT/HMAC). Any tampered or server-unissued token must be rejected — redirect to login, or 401/403 on API calls.

**Actual:** The server trusts whatever JSON the cookie decodes to. A user can grant themselves admin, or impersonate any agency, by editing their own cookie.

**Who is harmed, how badly, how reversible:**
- **Victim:** the entire platform and every tenant on it.
- **How badly:** full authentication bypass and privilege escalation — read AND write, with no privilege ceiling once role can be forged to admin. Note that this is independent of BUG-1: even if the API filter is fixed, a forged `agencyId` reopens the same door.
- **Reversibility:** low. Writes made under a forged identity persist and corrupt data provenance (e.g. note authorship, audit trails) in a way that can't be cleanly separated from legitimate activity afterward.
