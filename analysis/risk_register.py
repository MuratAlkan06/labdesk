"""LabDesk analysis — risk register ranked by probability × impact.

Standalone standard-library script (PRINCIPLES.md §8). Run from the repository
root:

    .venv/bin/python analysis/risk_register.py

Seven risks are registered across seven categories — organizational,
financial, resource, scope, technical, quality, and compliance. Probability
and impact are 1-5 ordinal ratings (not 0-1 probabilities), so the risk score
is their product on a 1-25 scale. The register is then ranked by descending
score; ``sorted`` is stable, so risks that tie keep the order they were listed
in below.

Two risks carry a note tying them to evidence from elsewhere in this project:
the cost risk to the Monte Carlo run, and the quality risk to a defect that
actually shipped past the unit tests during the build. The register itself is
deterministic — no simulation, so no seed — and all printing lives under the
``__main__`` guard so the module stays silent on import.
"""

# --- Parameters (the only numbers to edit; PRINCIPLES.md §8) -----------------

RATING_MIN = 1
RATING_MAX = 5
TOP_RISK_COUNT = 3

# (short name, risk, category, probability rating, impact rating, note).
# Probability and impact are 1-5 ordinal ratings; "" means the risk has no note.
RISKS = [
    (
        "low adoption",
        "Low adoption — staff keep using email and Slack",
        "Organizational",
        4,
        5,
        "",
    ),
    (
        "budget overrun",
        "Build cost exceeds the $25,000 budget",
        "Financial",
        4,
        4,
        "Monte Carlo puts P(cost > $25,000) at 67.8%.",
    ),
    (
        "key-person dependency",
        "Key-person dependency — one maintainer",
        "Resource",
        3,
        4,
        "",
    ),
    (
        "scope creep",
        "Scope creep from ad-hoc feature requests",
        "Scope",
        3,
        3,
        "",
    ),
    (
        "SQLite data loss",
        "SQLite data loss — no backup routine",
        "Technical",
        2,
        4,
        "",
    ),
    (
        "AI code defect",
        "AI-generated code defect ships despite green tests",
        "Quality",
        3,
        2,
        "Occurred once during the build — a UI-layer duration bug all 28 unit "
        "tests missed.",
    ),
    (
        "requester PII",
        "Requester PII mishandled in tickets",
        "Compliance",
        2,
        3,
        "",
    ),
]

# --- End of parameters -------------------------------------------------------


def validate_ratings(risks):
    """Raise unless every probability and impact sits on the 1-5 scale."""
    for _, risk, _, probability_rating, impact_rating, _ in risks:
        ratings = (
            ("probability", probability_rating),
            ("impact", impact_rating),
        )
        for field, rating in ratings:
            if not RATING_MIN <= rating <= RATING_MAX:
                raise ValueError(
                    f"{field} rating {rating} for {risk!r} is outside "
                    f"{RATING_MIN}-{RATING_MAX}"
                )


def risk_score(probability_rating, impact_rating):
    """Risk score on the 1-25 scale: probability × impact."""
    return probability_rating * impact_rating


def ranked_register(risks):
    """Rank ``risks`` by descending score, keeping listed order on ties.

    ``list.sort`` is stable and stays stable under ``reverse=True``, so two
    risks with the same score come out in the order they appear in ``RISKS``.
    Returns rows of ``(rank, short name, risk, category, probability, impact,
    score, note)``.
    """
    scored = [
        (
            short_name,
            risk,
            category,
            probability_rating,
            impact_rating,
            risk_score(probability_rating, impact_rating),
            note,
        )
        for short_name, risk, category, probability_rating, impact_rating, note
        in risks
    ]
    scored.sort(key=lambda row: row[5], reverse=True)
    return [(rank, *row) for rank, row in enumerate(scored, start=1)]


def numbered_notes(rows):
    """Number the notes carried by ``rows`` in rank order.

    Returns ``(markers, notes)``: ``markers`` maps a rank to its ``"[n]"``
    marker for the rows that carry a note, and ``notes`` is the matching list
    of ``(marker, note)`` pairs. Keeping the note text out of the table is
    what lets the table stay narrow enough to paste into the report.
    """
    markers = {}
    notes = []
    for row in rows:
        rank, note = row[0], row[-1]
        if note:
            marker = f"[{len(notes) + 1}]"
            markers[rank] = marker
            notes.append((marker, note))
    return markers, notes


def join_with_and(phrases):
    """Join phrases into prose: ``"a, b, and c"``."""
    if len(phrases) < 2:
        return "".join(phrases)
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


if __name__ == "__main__":
    validate_ratings(RISKS)

    rows = ranked_register(RISKS)
    markers, notes = numbered_notes(rows)
    categories = [category for _, _, _, category, _, _, _, _ in rows]

    print("=" * 95)
    print("LabDesk — Risk register (risk score = probability × impact)")
    print("=" * 95)
    print()

    print("Assumptions")
    print(
        f"  {'P = probability':<22}{RATING_MIN}-{RATING_MAX} ordinal rating, "
        f"{RATING_MAX} = near certain"
    )
    print(
        f"  {'I = impact':<22}{RATING_MIN}-{RATING_MAX} ordinal rating, "
        f"{RATING_MAX} = project-threatening"
    )
    print(
        f"  {'Score = P × I':<22}{RATING_MIN}-{RATING_MAX * RATING_MAX}, "
        "ranked descending; ties keep register order"
    )
    print(
        f"  {'Coverage':<22}{len(rows)} risks across "
        f"{len(set(categories))} categories"
    )
    print()

    header = (
        f"{'Rank':>4}  {'Risk':<50}  {'Category':<14}  {'P':>3}  {'I':>3}  "
        f"{'Score':>5}  {'Note':<4}"
    )
    print(header)
    print("-" * len(header))
    for rank, _, risk, category, probability, impact, score, _ in rows:
        line = (
            f"{rank:>4}  {risk:<50}  {category:<14}  {probability:>3}  "
            f"{impact:>3}  {score:>5}  {markers.get(rank, ''):<4}"
        )
        print(line.rstrip())
    print("-" * len(header))
    print()

    print("Notes")
    for marker, note in notes:
        print(f"  {marker}  {note}")
    print()

    top_risks = rows[:TOP_RISK_COUNT]
    top_phrases = [
        f"{short_name} ({score})"
        for _, short_name, _, _, _, _, score, _ in top_risks
    ]
    print(
        f"Read: the {TOP_RISK_COUNT} highest-priority risks are "
        f"{join_with_and(top_phrases)}."
    )
