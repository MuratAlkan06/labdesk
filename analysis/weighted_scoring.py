"""LabDesk analysis — weighted scoring model for project selection.

Standalone standard-library script (PRINCIPLES.md §8). Run from the repository
root:

    .venv/bin/python analysis/weighted_scoring.py

Two proposals compete for the same department budget and the same two-week
build window: the help-desk ticket system that was actually built, and a lab
equipment inventory and checkout system. Each is rated 1-10 against five
weighted criteria. A criterion's weighted score is ``weight × raw score`` and a
project's total is the sum of those five contributions, so a total lands back
on the same 1-10 scale as the raw ratings.

The weights are the model's only soft assumption, so the script refuses to run
unless they total 100 percent. The model is deterministic — no simulation, so
no seed. Every figure is computed in full precision and rounded only at print
time, and all printing lives under the ``__main__`` guard so the module stays
silent on import.
"""

import math

# --- Parameters (the only numbers to edit; PRINCIPLES.md §8) -----------------

PROJECT_A_NAME = "LabDesk — help-desk ticket system"
PROJECT_B_NAME = "LabTrack — lab equipment inventory and checkout system"

RAW_SCORE_MIN = 1
RAW_SCORE_MAX = 10

# (criterion, weight, raw score for A, raw score for B).
# Weights are 0-1 floats printed as percentages; they must total 1.0.
CRITERIA = [
    ("Strategic alignment with department goals", 0.25, 8, 6),
    ("Financial value (4-year NPV)", 0.20, 7, 6),
    ("Feasibility within a two-week build", 0.20, 9, 7),
    ("Adoption likelihood (user willingness to switch)", 0.15, 6, 7),
    ("Operational urgency (severity of current pain)", 0.20, 9, 5),
]

# --- End of parameters -------------------------------------------------------


def validate_weights(criteria):
    """Return the total criterion weight, or raise if it is not 1.0.

    A weighted scoring model whose weights do not total 100 percent produces
    totals that cannot be read against the raw-score scale, so this fails
    loudly rather than printing a plausible wrong number (PRINCIPLES.md §8).
    """
    total_weight = sum(weight for _, weight, _, _ in criteria)
    if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        raise ValueError(
            f"criterion weights must total 1.0 (100%), got {total_weight:.4f}"
        )
    return total_weight


def validate_raw_scores(criteria):
    """Raise unless every raw score sits on the 1-10 scale."""
    for criterion, _, raw_score_a, raw_score_b in criteria:
        for project, raw_score in (("A", raw_score_a), ("B", raw_score_b)):
            if not RAW_SCORE_MIN <= raw_score <= RAW_SCORE_MAX:
                raise ValueError(
                    f"raw score {raw_score} for project {project} on "
                    f"{criterion!r} is outside "
                    f"{RAW_SCORE_MIN}-{RAW_SCORE_MAX}"
                )


def weighted_score(weight, raw_score):
    """One criterion's contribution to a project total: weight × raw score."""
    return weight * raw_score


def score_rows(criteria):
    """Rows of ``(criterion, weight, A raw, A weighted, B raw, B weighted)``."""
    return [
        (
            criterion,
            weight,
            raw_score_a,
            weighted_score(weight, raw_score_a),
            raw_score_b,
            weighted_score(weight, raw_score_b),
        )
        for criterion, weight, raw_score_a, raw_score_b in criteria
    ]


def total_weighted_score(rows, project):
    """Total weighted score for ``project``, either ``"A"`` or ``"B"``."""
    if project == "A":
        return sum(weighted_a for _, _, _, weighted_a, _, _ in rows)
    if project == "B":
        return sum(weighted_b for _, _, _, _, _, weighted_b in rows)
    raise ValueError(f"unknown project {project!r}: expected 'A' or 'B'")


if __name__ == "__main__":
    total_weight = validate_weights(CRITERIA)
    validate_raw_scores(CRITERIA)

    rows = score_rows(CRITERIA)
    total_a = total_weighted_score(rows, "A")
    total_b = total_weighted_score(rows, "B")

    print("=" * 88)
    print("LabDesk — Weighted scoring model: project selection")
    print("=" * 88)
    print()

    print("Candidates")
    print(f"  {'Project A':<12}{PROJECT_A_NAME}")
    print(f"  {'Project B':<12}{PROJECT_B_NAME}")
    print()

    print("Assumptions")
    print(
        f"  {'Raw score scale':<26}{RAW_SCORE_MIN}-{RAW_SCORE_MAX}, "
        "higher is better"
    )
    print(f"  {'Criterion weights total':<26}{total_weight * 100:.0f}%")
    print(f"  {'Weighted score (wtd)':<26}weight × raw score")
    print(f"  {'Project total':<26}sum of the five weighted scores")
    print()

    header = (
        f"{'Criterion':<48}  {'Weight':>6}  {'A raw':>6}  {'A wtd':>6}  "
        f"{'B raw':>6}  {'B wtd':>6}"
    )
    print(header)
    print("-" * len(header))
    for criterion, weight, raw_a, weighted_a, raw_b, weighted_b in rows:
        print(
            f"{criterion:<48}  {weight * 100:>5.0f}%  {raw_a:>6}  "
            f"{weighted_a:>6.2f}  {raw_b:>6}  {weighted_b:>6.2f}"
        )
    print("-" * len(header))
    print(
        f"{'Total':<48}  {total_weight * 100:>5.0f}%  {'':>6}  {total_a:>6.2f}  "
        f"{'':>6}  {total_b:>6.2f}"
    )
    print()

    print("Result")
    print(f"  {'Project A total':<18}{total_a:>7.2f}   {PROJECT_A_NAME}")
    print(f"  {'Project B total':<18}{total_b:>7.2f}   {PROJECT_B_NAME}")
    print(f"  {'Margin (A - B)':<18}{total_a - total_b:>7.2f}")
    print()

    leading_project = "A" if total_a >= total_b else "B"
    leading_total = max(total_a, total_b)
    trailing_total = min(total_a, total_b)
    print(
        f"Weighted totals favor Project {leading_project}, "
        f"{leading_total:.2f} vs {trailing_total:.2f}."
    )
