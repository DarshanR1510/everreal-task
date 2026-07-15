"""
rubric.py — scoring criteria for the Playwright-test judge, as data.

Each criterion is a single, narrow, checkable question the judge answers
about ONE candidate test — e.g. "does the test assert X" rather than a
vague "is the test good". judge.py sends every criterion's `question`
to the model verbatim and expects exactly one result back per criterion,
in order, so keep each one self-contained (the model sees no other context
about your intent beyond what's written here).

Do NOT invent the full rubric here — you are defining the criteria; this
file only holds the data structure judge.py and meta_eval.py consume.
"""

from typing import TypedDict


class Criterion(TypedDict):
    name: str
    question: str


RUBRIC: list[Criterion] = [
    {
        "name": "asserts_fixed_not_buggy",
        "question": "Does the test assert the CORRECT/fixed behavior, so it "
                    "fails against the current buggy build and passes once "
                    "fixed? A test that asserts the current buggy behavior "
                    "(e.g. expects HTTP 200 for a cross-tenant read) as "
                    "'expected' is BAD — it would go green and permanently "
                    "protect the bug.",
    },
    {
        "name": "no_false_green_fallback",
        "question": "Does the test avoid assertions that can pass without "
                    "proving anything? Examples of FAILURES: a `?? defaultValue` "
                    "fallback that substitutes the correct value when a field "
                    "is absent; a subset check that also accepts an empty set; "
                    "asserting an element merely exists rather than has the "
                    "correct value. The assertion must fail loudly on "
                    "missing/malformed data, not default to passing.",
    },
    {
        "name": "verifies_real_artifact",
        "question": "For any test involving a file, download, export, or API "
                    "payload, does it actually read and parse that artifact and "
                    "assert on its real contents? A CSV/export test that only "
                    "checks a UI toast or a button state — without opening the "
                    "file — proves nothing and is BAD.",
    },
    {
        "name": "severity_names_victim_and_blast_radius",
        "question": "Does the test's comment/documentation state severity in "
                    "terms of WHO is harmed, HOW badly, and whether it's "
                    "REVERSIBLE? A severity label with no named victim and no "
                    "blast radius is BAD.",
    },
    {
        "name": "targets_real_risk",
        "question": "Does the test target a genuine risk (authorization, "
                    "tenant isolation, data integrity, injection) rather than "
                    "trivial padding (e.g. checking a placeholder text or a "
                    "static label)? Depth over breadth — padding is BAD.",
    },
    {
        "name": "stable_locators",
        "question": "Does the test use resilient locators (getByRole, "
                    "getByLabel, getByTestId) rather than brittle CSS classes "
                    "or deep XPath that a refactor would silently break? "
                    "Brittle locators where a stable one was available is a "
                    "weakness.",
    },
]
