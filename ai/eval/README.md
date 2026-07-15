# AI test-quality eval harness

A small, dependency-light Python harness that scores AI-generated Playwright
tests against a rubric using an LLM-as-judge, and then **validates the judge
itself** against a hand-labeled golden set. Only dependency: `anthropic`
(plus the standard library).

## What it does

There are two distinct evaluations layered here, and it's important to keep
them separate:

1. **Judging candidate tests** (`judge.py`): given one Playwright test
   snippet and a rubric (`rubric.py`), ask Claude to score the snippet
   against each rubric criterion and return a structured `GOOD`/`BAD`
   verdict with per-criterion reasoning.
2. **Judging the judge** (`meta_eval.py`): given a golden set of test
   snippets that a human has already reviewed and labeled `GOOD`/`BAD`
   (`golden_set.py`), run the judge over every labeled item and measure how
   often the judge's verdict matches the human label.

Only step 2 is wired up to print a report right now (`run.py` runs the
meta-eval). Step 1's `judge_candidate()` function is the building block you
can call directly on any new, unlabeled candidate test once you trust the
judge (see "Using the judge directly" below).

## Why the meta-eval matters

Using an LLM to grade AI-generated tests is easy; trusting the grade is not.
Without a check on the judge, "the judge said GOOD" and "the test is
actually good" are two different claims that can silently diverge — the
judge might be lenient, might misread the rubric, might be swayed by
confident-sounding comments in the code instead of verifying them. The
meta-eval is that check: it holds the judge to a small set of examples a
human has already made a call on, and reports exactly where the judge's
verdict disagrees with that human call.

**A disagreement means the judge needs tuning — not that the human label was
wrong.** The golden-set labels are the ground truth this harness exists to
protect. If the judge and a label disagree, the fix is to adjust the rubric
wording, the judge's system prompt, or the model — not to second-guess the
label. `meta_eval.py` and its report are written to frame every
disagreement that way on purpose.

This is also the point of the exercise: the deliverable isn't "used an LLM
to grade tests," it's "built a way to know whether that grading can be
trusted, and by how much" — i.e. judgment applied on top of AI, not AI used
in place of judgment.

## Files

| File | Purpose |
|---|---|
| `rubric.py` | The scoring criteria, as data. Ships with 2 placeholder criteria only — you define the real rubric. |
| `golden_set.py` | Hand-labeled test snippets used to validate the judge. Ships with 2 placeholder entries (`human_label: "TODO"`) — you paste in real snippets and label them yourself. |
| `judge.py` | Calls the Anthropic API with one candidate test + the rubric, returns a parsed, structured verdict. |
| `meta_eval.py` | Runs the judge over every labeled item in the golden set, compares each verdict to your label, builds the agreement report. |
| `run.py` | Entrypoint — `python -m ai.eval.run` runs the meta-eval and prints the report. |

## Before you run it

1. **Fill in `rubric.py`.** Replace the two `PLACEHOLDER_*` entries with your
   real criteria. Each criterion is one narrow, checkable question — the
   judge sees only the `description` text, with no other context about your
   intent, so write it as a self-contained instruction.
2. **Fill in `golden_set.py`.** Replace the two placeholder entries with real
   Playwright test snippets. For each one, set `human_label` to `"GOOD"` or
   `"BAD"` based on your own independent review, and fill in `reason`. Items
   left with `human_label == "TODO"` are skipped (not scored) by the
   meta-eval, and listed under "SKIPPED" in the report.
3. **Set your API key** (never hardcoded — read from the environment):
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
   Running without it fails immediately with a clear error, not a silent
   no-op.
4. **Install the one dependency**:
   ```bash
   pip install -r ai/eval/requirements.txt
   ```

## How to run it

From the repo root:
```bash
python -m ai.eval.run
```

This runs `judge_candidate()` over every non-`"TODO"` item in `GOLDEN_SET`
and prints a report with:
- **Scored items** — how many golden-set items had a real label and got a
  parseable judge verdict.
- **Agreements** / **Disagreements** — counts.
- **Agreement rate** — agreements ÷ scored items.
- One line per disagreement: the snippet name, your label, the judge's
  verdict, and the judge's stated reason — so you can see exactly where and
  why the judge diverged and go tune the rubric/prompt accordingly.
- A **SKIPPED** section for any item still labeled `"TODO"`, or where the
  judge's response failed to parse as valid JSON (an `ERROR` verdict — these
  are never silently counted as agreements or disagreements).

## Using the judge directly

Once the meta-eval shows an agreement rate you trust, score a new,
unlabeled candidate test directly:

```python
from ai.eval.judge import judge_candidate

result = judge_candidate("my-new-test.spec.ts", open("my-new-test.spec.ts").read())
print(result.verdict)          # "GOOD" | "BAD" | "ERROR"
print(result.overall_reason)
for c in result.criteria:
    print(c.name, c.passed, c.reason)
```
