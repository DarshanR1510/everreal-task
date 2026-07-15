# AI Operator Artifact

## What's here
- `prompts/` — the actual prompts I gave Claude Code to scaffold the repo and generate the tests
- `raw-output/` — what the AI produced, unedited
- `corrections.md` — what I changed, and why
- `eval/` — an LLM-judge harness that scores AI-generated tests against a rubric I defined, validated against a hand-labeled golden set
- `not-trusted.md` — 3 things I would not trust an AI to do here

## How I used AI
AI wrote the mechanics: repo scaffold, test boilerplate, CSV parsing helpers,
the eval harness plumbing. I owned the judgment: which risks rank highest,
severity calls, authorization assertions, what "good" means in the rubric,
and the golden-set labels. The eval harness exists to prove that separation —
the AI scores at scale, but I validate the scorer against my own labels before
trusting a single number.