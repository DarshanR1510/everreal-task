"""
judge.py — LLM-as-judge: sends one candidate Playwright test, plus the
rubric from rubric.py, to Claude and returns a structured, parsed verdict.

Parsing is defensive on purpose: a judge is only as trustworthy as its
output is inspectable, so a response that isn't valid JSON in the expected
shape becomes an explicit ERROR verdict rather than being coerced into a
silent pass/fail.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any

import anthropic

from ai.eval.rubric import RUBRIC

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are a strict code reviewer scoring a single Playwright test against a fixed rubric.

Score ONLY against the rubric criteria given to you in the user message. Do not invent additional criteria, do not apply style preferences outside the rubric, and do not be swayed by confident-sounding comments inside the candidate test itself — verify claims against the actual code.

Return ONLY valid JSON. No prose before or after it, no explanation outside the JSON fields, no markdown code fences. The JSON must match exactly this shape:

{
  "criteria": [
    {"name": "<criterion name, copied exactly from the rubric>", "passed": true|false, "reason": "<one or two sentences>"}
  ],
  "verdict": "GOOD" | "BAD",
  "overall_reason": "<one or two sentences summarizing the verdict>"
}

Include exactly one entry in "criteria" for every criterion you were given, in the same order, using the same "name" values. "verdict" must be "GOOD" only if the candidate passes every criterion; otherwise "BAD"."""


@dataclass
class CriterionResult:
    name: str
    passed: bool
    reason: str


@dataclass
class JudgeResult:
    verdict: str  # "GOOD" | "BAD" | "ERROR"
    criteria: list[CriterionResult] = field(default_factory=list)
    overall_reason: str = ""
    raw_response: str = ""


def _load_dotenv_if_present() -> None:
    """Best-effort, stdlib-only .env loader.

    This repo's Playwright side loads .env via the Node `dotenv` package;
    Python doesn't read it automatically. Rather than adding a Python
    dotenv dependency, just parse simple KEY=VALUE lines from the repo-root
    .env ourselves if ANTHROPIC_API_KEY isn't already in the environment.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _client() -> anthropic.Anthropic:
    _load_dotenv_if_present()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it before running the "
            "harness, or add it to a .env file at the repo root, e.g.:\n\n"
            "    export ANTHROPIC_API_KEY=sk-ant-...\n"
        )
    return anthropic.Anthropic(api_key=api_key)


def _build_user_message(candidate_name: str, candidate_code: str) -> str:
    rubric_lines = "\n".join(f"- {c['name']}: {c['question']}" for c in RUBRIC)
    return (
        f"RUBRIC (score against these and only these):\n{rubric_lines}\n\n"
        f"CANDIDATE TEST NAME: {candidate_name}\n\n"
        f"CANDIDATE TEST CODE:\n```typescript\n{candidate_code}\n```"
    )


def _strip_code_fences(text: str) -> str:
    """Strip a leading/trailing ```/```json fence if the model added one
    despite being told not to — judges don't always follow instructions."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def judge_candidate(candidate_name: str, candidate_code: str) -> JudgeResult:
    """Send one candidate test to Claude and parse its structured verdict.

    Never raises on a malformed model response — any failure to parse the
    expected JSON shape becomes an ERROR verdict, not a silent GOOD or BAD,
    since a malformed judge response says nothing about the candidate test.
    """
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_message(candidate_name, candidate_code),
            }
        ],
    )

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    cleaned = _strip_code_fences(raw_text)

    try:
        data: dict[str, Any] = json.loads(cleaned)

        verdict = data["verdict"]
        if verdict not in ("GOOD", "BAD"):
            raise ValueError(f"unexpected verdict value: {verdict!r}")

        criteria = [
            CriterionResult(
                name=c["name"],
                passed=bool(c["passed"]),
                reason=c.get("reason", ""),
            )
            for c in data["criteria"]
        ]

        return JudgeResult(
            verdict=verdict,
            criteria=criteria,
            overall_reason=data.get("overall_reason", ""),
            raw_response=raw_text,
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        return JudgeResult(
            verdict="ERROR",
            criteria=[],
            overall_reason=f"Failed to parse judge response: {exc}",
            raw_response=raw_text,
        )
