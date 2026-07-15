# What I would NOT trust an AI to do here

1. **Authorization assertions.** AI generated a cross-tenant test with a
   fallback that made it pass even when the tenant field was missing. Whether
   a user should be BLOCKED from data is a security judgment; AI defaults to
   asserting whatever the app currently returns. A human has to own the
   "who is allowed to see this" line.

2. **Severity calls.** AI can describe a bug but cannot decide who is harmed,
   how badly, and whether it's reversible. It rated things by discovery order
   or generic labels. Naming the victim and blast radius — e.g. that the
   cross-tenant leak exposes confidential VIP portfolio owners across every
   agency — is an ownership call, not a pattern-match.

3. **Exact-value oracles.** AI is happy to assert an element "exists" or a
   response "is 200" — checks that pass without proving correctness. Deciding
   the exact expected value (the tenant filter returns ONLY my agency's data,
   the exported cell is NOT a live formula) requires knowing what correct
   actually means for this domain. AI produces green tests that verify nothing
   unless a human defines the real oracle.