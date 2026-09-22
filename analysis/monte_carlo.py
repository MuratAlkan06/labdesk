"""LabDesk analysis — Monte Carlo simulation of the build's total cost.

Standalone script (PRINCIPLES.md §8). Run from the repository root:

    .venv/bin/python analysis/monte_carlo.py

Each trial draws developer hours, an hourly rate, and a rework multiplier, then
totals them with the fixed tooling cost:

    cost = hours * rate * rework + fixed cost

The math is standard library only (``random``, ``statistics``, ``math``);
matplotlib is used solely to write the histogram, on the Agg backend so the
script never needs a display. The seed is the first executable statement of
main, so the printed statistics and the PNG are reproducible run to run.

Every ``random.triangular`` call below passes keyword arguments: ``mode`` is
the THIRD positional parameter, and the classic arg-order bug is exactly what
PRINCIPLES.md §8 forbids.
"""

import math
import os
import random
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # No display needed; must precede the pyplot import.
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

# --- Parameters (the only numbers to edit; PRINCIPLES.md §8) -----------------

N_TRIALS = 10_000
SEED = 42

FIXED_COST_USD = 2_500

# Developer hours: triangular(low, high, mode) — mode is the third argument.
HOURS_LOW = 220
HOURS_HIGH = 380
HOURS_MODE = 300

# Blended hourly rate: uniform between these bounds.
RATE_LOW_USD = 65
RATE_HIGH_USD = 85

# Rework multiplier: 1.00 means no rework, 1.20 means a fifth of the work again.
REWORK_LOW = 1.00
REWORK_HIGH = 1.20
REWORK_MODE = 1.03

# Reference lines reported and drawn on the histogram.
BUDGET_USD = 25_000
BREAK_EVEN_USD = 28_529

HISTOGRAM_BINS = 50
HISTOGRAM_PATH = Path(__file__).with_name("monte_carlo.png")

# --- End of parameters -------------------------------------------------------


def format_usd(amount_usd, decimals=0):
    """Format dollars with a thousands separator, e.g. ``$26,725``."""
    sign = "-" if amount_usd < 0 else ""
    return f"{sign}${abs(amount_usd):,.{decimals}f}"


def simulate_trial_cost():
    """One simulated total cost in dollars.

    ``mode`` is ``random.triangular``'s third positional parameter, so both
    draws name their arguments (PRINCIPLES.md §8).
    """
    hours = random.triangular(low=HOURS_LOW, high=HOURS_HIGH, mode=HOURS_MODE)
    rate_usd = random.uniform(RATE_LOW_USD, RATE_HIGH_USD)
    rework = random.triangular(low=REWORK_LOW, high=REWORK_HIGH, mode=REWORK_MODE)
    return hours * rate_usd * rework + FIXED_COST_USD


def run_simulation(n_trials):
    """Return a list of ``n_trials`` simulated total costs."""
    return [simulate_trial_cost() for _ in range(n_trials)]


def percentile(sorted_values, p):
    """The ``p``-th percentile (0-100) of an already-sorted sample.

    Convention: linear interpolation between the two nearest order statistics
    (the same rule as ``statistics.quantiles(method="inclusive")``). Chosen over
    nearest-rank so the reported percentiles do not jump with the trial count.
    """
    if not sorted_values:
        raise ValueError("percentile is undefined for an empty sample")
    rank = (len(sorted_values) - 1) * (p / 100.0)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = rank - lower_index
    return (
        sorted_values[lower_index] * (1.0 - weight)
        + sorted_values[upper_index] * weight
    )


def probability_above(values, threshold_usd):
    """Share of trials whose cost strictly exceeds ``threshold_usd`` (0-1)."""
    return sum(1 for value in values if value > threshold_usd) / len(values)


def save_histogram(values, path):
    """Write the cost histogram with the budget and break-even lines marked."""
    figure, axes = plt.subplots(figsize=(9, 5.5))
    axes.hist(values, bins=HISTOGRAM_BINS, color="#4C72B0", edgecolor="white")
    axes.axvline(
        BUDGET_USD,
        color="#C44E52",
        linestyle="--",
        linewidth=2,
        label=f"Budget {format_usd(BUDGET_USD)}",
    )
    axes.axvline(
        BREAK_EVEN_USD,
        color="#55A868",
        linestyle="-.",
        linewidth=2,
        label=f"Break-even {format_usd(BREAK_EVEN_USD)}",
    )
    # A bare format string makes matplotlib build the StrMethodFormatter, so
    # the cost axis reads "$25,000" instead of "25000".
    axes.xaxis.set_major_formatter("${x:,.0f}")
    axes.set_xlabel("Simulated total cost ($)")
    axes.set_ylabel("Trials")
    axes.set_title(
        f"LabDesk build cost — {len(values):,} Monte Carlo trials (seed {SEED})"
    )
    axes.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    random.seed(SEED)

    costs_usd = run_simulation(N_TRIALS)
    sorted_costs_usd = sorted(costs_usd)

    mean_usd = statistics.fmean(costs_usd)
    median_usd = statistics.median(costs_usd)
    p10_usd = percentile(sorted_costs_usd, 10)
    p80_usd = percentile(sorted_costs_usd, 80)
    p90_usd = percentile(sorted_costs_usd, 90)
    p_over_budget = probability_above(costs_usd, BUDGET_USD)
    p_over_break_even = probability_above(costs_usd, BREAK_EVEN_USD)

    print("=" * 66)
    print("LabDesk — Monte Carlo simulation of total build cost")
    print("=" * 66)
    print()

    print("Assumptions")
    print(f"  {'Trials':<34}{N_TRIALS:>18,}")
    print(f"  {'Random seed':<34}{SEED:>18}")
    print(f"  {'Fixed cost':<34}{format_usd(FIXED_COST_USD):>18}")
    print(
        f"  {'Hours (triangular low/mode/high)':<34}"
        f"{f'{HOURS_LOW} / {HOURS_MODE} / {HOURS_HIGH}':>18}"
    )
    print(
        f"  {'Hourly rate (uniform low/high)':<34}"
        f"{f'${RATE_LOW_USD} / ${RATE_HIGH_USD}':>18}"
    )
    print(
        f"  {'Rework (triangular low/mode/high)':<34}"
        f"{f'{REWORK_LOW:.2f} / {REWORK_MODE:.2f} / {REWORK_HIGH:.2f}':>18}"
    )
    print()

    header = f"{'Statistic':<28}  {'Value':>12}"
    print(header)
    print("-" * len(header))
    print(f"{'Mean cost':<28}  {format_usd(mean_usd):>12}")
    print(f"{'Median cost (P50)':<28}  {format_usd(median_usd):>12}")
    print(f"{'P10 (optimistic)':<28}  {format_usd(p10_usd):>12}")
    print(f"{'P80':<28}  {format_usd(p80_usd):>12}")
    print(f"{'P90 (pessimistic)':<28}  {format_usd(p90_usd):>12}")
    print("-" * len(header))
    print(
        f"{f'P(cost > {format_usd(BUDGET_USD)})':<28}  {p_over_budget * 100:>11.1f}%"
    )
    print(
        f"{f'P(cost > {format_usd(BREAK_EVEN_USD)})':<28}  "
        f"{p_over_break_even * 100:>11.1f}%"
    )
    print("-" * len(header))
    print()

    save_histogram(costs_usd, HISTOGRAM_PATH)
    print(f"Histogram written to {os.path.relpath(HISTOGRAM_PATH)}")
    print()
    print(
        f"Read: {p_over_budget * 100:.0f}% of trials exceed the "
        f"{format_usd(BUDGET_USD)} budget and {p_over_break_even * 100:.0f}% "
        f"exceed the {format_usd(BREAK_EVEN_USD)} break-even cost. Percentiles "
        "use linear interpolation between order statistics."
    )
