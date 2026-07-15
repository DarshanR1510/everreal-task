"""
meta_eval.py — validates the JUDGE against the hand-labeled golden set.

Why this matters: an LLM-as-judge is only useful if it agrees with a
careful human reviewer often enough to be trusted on NEW, unlabeled tests
later. This module is a check on the judge, not on the candidate tests in
the golden set. A disagreement here means the JUDGE needs tuning — its
prompt, the rubric wording, or the model choice — not that the human label
was wrong. The golden-set labels in golden_set.py are the ground truth this
harness exists to protect; the judge is the thing under test.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.eval.golden_set import GOLDEN_SET
from ai.eval.judge import JudgeResult, judge_candidate


@dataclass
class Disagreement:
    name: str
    human_label: str
    judge_verdict: str
    judge_reason: str


@dataclass
class MetaEvalReport:
    total: int
    agreements: int
    disagreements: list[Disagreement]
    skipped: list[str]

    @property
    def agreement_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.agreements / self.total


def run_meta_eval() -> MetaEvalReport:
    disagreements: list[Disagreement] = []
    skipped: list[str] = []
    agreements = 0

    for item in GOLDEN_SET:
        if item["human_label"] == "TODO":
            skipped.append(
                f"{item['name']}: human_label is still 'TODO' — label this item before it can be scored."
            )
            continue

        result: JudgeResult = judge_candidate(item["name"], item["code"])

        if result.verdict == "ERROR":
            skipped.append(f"{item['name']}: judge returned ERROR — {result.overall_reason}")
            continue

        if result.verdict == item["human_label"]:
            agreements += 1
        else:
            disagreements.append(
                Disagreement(
                    name=item["name"],
                    human_label=item["human_label"],
                    judge_verdict=result.verdict,
                    judge_reason=result.overall_reason,
                )
            )

    scored = agreements + len(disagreements)
    return MetaEvalReport(
        total=scored,
        agreements=agreements,
        disagreements=disagreements,
        skipped=skipped,
    )


def print_report(report: MetaEvalReport) -> None:
    print("=" * 70)
    print("JUDGE VALIDATION REPORT (meta-eval)")
    print("=" * 70)
    print(
        "This measures whether the JUDGE can be trusted. Every disagreement\n"
        "below is a signal to fix the JUDGE (prompt, rubric wording, or model\n"
        "choice) — not a reason to doubt the hand-assigned human labels."
    )
    print()

    if report.skipped:
        print(f"SKIPPED ({len(report.skipped)}):")
        for s in report.skipped:
            print(f"  - {s}")
        print()

    print(f"Scored items:     {report.total}")
    print(f"Agreements:       {report.agreements}")
    print(f"Disagreements:    {len(report.disagreements)}")
    print(f"Agreement rate:   {report.agreement_rate * 100:.1f}%")
    print()

    if report.disagreements:
        print("DISAGREEMENTS (judge needs tuning):")
        for d in report.disagreements:
            print(f"  - {d.name}")
            print(f"      your label:    {d.human_label}")
            print(f"      judge verdict: {d.judge_verdict}")
            print(f"      judge reason:  {d.judge_reason}")
        print()
    elif report.total > 0:
        print("No disagreements among scored items.")
        print()

    print("=" * 70)
