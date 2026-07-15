## BUG-4 — Saved view ignores its filter (shows all contacts instead of the filtered subset)
**Severity: MEDIUM**

**Repro:**
1. Open a saved/shared search view (e.g. via the Views button on `/contacts` or `/views`).
2. The view is meant to show a filtered subset (e.g. "München prospects").
3. Instead, it returns the full contact list — all 14 contacts — ignoring the saved filter.

**Expected:** Opening a saved view shows only the contacts matching that view's filter — a proper, non-empty subset of the full list.

**Actual:** The filter is not applied; the full list is returned regardless of the saved view.

**Who is harmed, how badly, how reversible:**
- **Victim:** the agent relying on the saved view to work a specific segment.
- **How badly:** the agent acts on the wrong dataset — contacts the view was supposed to exclude. Functional correctness failure, but no data leak beyond the agent's own agency (assuming BUG-1 is fixed) and no data loss.
- **Reversibility:** fully reversible — it's a display/query bug, nothing is corrupted.
