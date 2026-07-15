# Corrections — where I overrode the AI

## 1. False-green fallback in cross-tenant test (highest-value catch)
AI generated:
    expect(body.contact?.agencyId ?? 'alpen-immobilien').toBe('alpen-immobilien');
Problem: the `?? 'alpen-immobilien'` fallback makes the test pass when the
agencyId field is ABSENT — it substitutes the correct value and asserts it
against itself. The test would go green on a malformed or empty response,
proving nothing.
My fix: removed the fallback so the assertion fails loudly when the field is
missing. A regression test that can pass without the field present is worse
than no test — it manufactures false confidence.

## 2. Empty-subset false pass in Views test
The subset assertion would also pass if the view returned ZERO contacts
(empty set is a subset of everything). Same failure pattern as #1 — an
assertion that's technically true but proves nothing.
My fix: assert the result is a proper, NON-EMPTY subset.

## 3. Risk of asserting buggy behavior as expected
When asked to write regression tests, the default AI tendency is to assert
whatever the app currently does — which here would mean asserting the buggy
HTTP 200 cross-tenant response as "expected." I explicitly directed it to
assert CORRECT behavior so tests fail against the current build and pass
only once fixed. Left unchecked, AI writes tests that protect bugs.

## 4. Meta-eval caught my own data error
"My meta-eval sat at 50% and stayed there after I fixed the placeholder data. The judge was scoring my GOOD examples as BAD. When I traced it, the judge was correct: my rubric requires every criterion to pass, including 'severity documented in comments,' but my golden GOOD snippets were bare assertion fragments with no comment blocks — so they legitimately failed that criterion. The bug was in my golden set, not the judge. I fixed it by using the full test bodies as the GOOD examples. Lesson: an all-or-nothing rubric punishes fragments that are correct-but-incomplete; a production version should score per-criterion applicability rather than demanding all criteria on every test."