"""
run.py — entrypoint. `python -m ai.eval.run` runs the meta-eval (judge vs.
hand-labeled golden set) and prints the judge validation report.
"""

from ai.eval.meta_eval import print_report, run_meta_eval


def main() -> None:
    report = run_meta_eval()
    print_report(report)


if __name__ == "__main__":
    main()
