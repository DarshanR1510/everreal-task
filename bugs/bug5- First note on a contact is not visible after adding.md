## BUG-5 — First note on a contact is not visible after adding
**Severity: LOW**

**Repro:**
1. Open any contact with no existing notes.
2. Add a note.
3. The first note does not appear in the notes list (subsequent notes render fine).

**Expected:** Every note added should appear immediately in the contact's notes list.

**Actual:** The first note added to a contact does not render (data appears to save; it's a display/refresh issue).

**Who is harmed, how badly, how reversible:**
- **Victim:** the agent adding notes.
- **How badly:** minor. The note appears saved but invisible, which can cause confusion or duplicate notes. No data loss, no exposure.
- **Reversibility:** fully reversible — a frontend render/state bug; refreshing or reloading typically surfaces the note.
