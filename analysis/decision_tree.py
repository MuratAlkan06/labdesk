"""LabDesk analysis — commit to the full build now, or run a pilot first?

Standalone standard-library script (PRINCIPLES.md §8). Run from the repository
root:

    .venv/bin/python analysis/decision_tree.py

Two decisions are compared on expected monetary value (EMV):

  COMMIT  build the whole desk now and live with whichever adoption arrives.
  PILOT   spend a small sum on a four-week pilot, then build only if adoption
          looks high — the pilot buys the option to stop.

The NPV helpers below are deliberately duplicated from ``analysis/npv.py``
rather than imported, so each analysis script runs on its own and can be read
end to end in the report. There is no randomness here, so there is no seed.
"""

# --- Parameters (the only numbers to edit; PRINCIPLES.md §8) -----------------

P_HIGH_ADOPTION = 0.6
PILOT_COST_USD = 2_000

# Same build economics as analysis/npv.py, restated so this file stands alone.
INITIAL_COST_USD = 25_000
ANNUAL_GROSS_BENEFIT_USD = 12_000
ANNUAL_MAINTENANCE_USD = 3_000
DISCOUNT_RATE = 0.10
YEARS = 4

# Under low adoption the desk is used far less, so only 40 percent of the
# gross benefit lands. Maintenance is unchanged: the desk still has to run.
LOW_ADOPTION_BENEFIT_SHARE = 0.4

# --- End of parameters -------------------------------------------------------

# Derived from the parameters above, not knobs of their own.
P_LOW_ADOPTION = 1.0 - P_HIGH_ADOPTION


def format_usd(amount_usd, decimals=0):
    """Format dollars with a thousands separator, e.g. ``-$25,000``."""
    sign = "-" if amount_usd < 0 else ""
    return f"{sign}${abs(amount_usd):,.{decimals}f}"


def annuity_factor(discount_rate, years):
    """Sum of the discount factors for years 1..``years`` (≈3.169865 here)."""
    return sum(1.0 / ((1.0 + discount_rate) ** year) for year in range(1, years + 1))


def net_present_value(initial_cost_usd, annual_cash_flow_usd, discount_rate, years):
    """NPV of paying ``initial_cost_usd`` now for a level annual cash flow."""
    return annual_cash_flow_usd * annuity_factor(discount_rate, years) - initial_cost_usd


def adoption_net_cash_flow(benefit_share):
    """Annual net cash flow when only ``benefit_share`` of the benefit lands."""
    return ANNUAL_GROSS_BENEFIT_USD * benefit_share - ANNUAL_MAINTENANCE_USD


def expected_monetary_value(outcomes):
    """EMV of ``(probability, value_usd)`` pairs."""
    return sum(probability * value_usd for probability, value_usd in outcomes)


if __name__ == "__main__":
    high_net_cash_flow_usd = adoption_net_cash_flow(1.0)
    low_net_cash_flow_usd = adoption_net_cash_flow(LOW_ADOPTION_BENEFIT_SHARE)

    high_npv_usd = net_present_value(
        INITIAL_COST_USD, high_net_cash_flow_usd, DISCOUNT_RATE, YEARS
    )
    low_npv_usd = net_present_value(
        INITIAL_COST_USD, low_net_cash_flow_usd, DISCOUNT_RATE, YEARS
    )

    # COMMIT: build now, take whichever adoption arrives.
    commit_outcomes = [
        ("High adoption", P_HIGH_ADOPTION, high_npv_usd),
        ("Low adoption", P_LOW_ADOPTION, low_npv_usd),
    ]
    commit_emv_usd = expected_monetary_value(
        [(probability, value_usd) for _, probability, value_usd in commit_outcomes]
    )

    # PILOT: pay the pilot cost, then build only if adoption looks high.
    pilot_proceed_usd = high_npv_usd - PILOT_COST_USD
    pilot_stop_usd = -PILOT_COST_USD
    pilot_outcomes = [
        ("High adoption -> proceed", P_HIGH_ADOPTION, pilot_proceed_usd),
        ("Low adoption -> stop", P_LOW_ADOPTION, pilot_stop_usd),
    ]
    pilot_emv_usd = expected_monetary_value(
        [(probability, value_usd) for _, probability, value_usd in pilot_outcomes]
    )

    print("=" * 66)
    print("LabDesk — Decision tree: commit now vs. pilot first")
    print("=" * 66)
    print()

    print("Assumptions")
    print(f"  {'P(high adoption)':<34}{P_HIGH_ADOPTION * 100:>11.0f}%")
    print(f"  {'P(low adoption)':<34}{P_LOW_ADOPTION * 100:>11.0f}%")
    print(f"  {'Pilot cost (4 weeks)':<34}{format_usd(PILOT_COST_USD):>12}")
    print(
        f"  {'Net cash flow, high adoption':<34}"
        f"{format_usd(high_net_cash_flow_usd):>12}   per year"
    )
    print(
        f"  {'Net cash flow, low adoption':<34}"
        f"{format_usd(low_net_cash_flow_usd):>12}   per year"
    )
    print(
        f"  {'Build NPV, high adoption':<34}{format_usd(high_npv_usd, 2):>12}"
    )
    print(f"  {'Build NPV, low adoption':<34}{format_usd(low_npv_usd, 2):>12}")
    print()

    header = (
        f"{'Decision':<8}  {'Branch':<26}  {'Prob.':>6}  "
        f"{'Outcome':>13}  {'Contribution':>13}"
    )
    print(header)
    print("-" * len(header))
    for label, probability, value_usd in commit_outcomes:
        print(
            f"{'COMMIT':<8}  {label:<26}  {probability:>6.2f}  "
            f"{format_usd(value_usd, 2):>13}  "
            f"{format_usd(probability * value_usd, 2):>13}"
        )
    print(
        f"{'':<8}  {'EMV (commit)':<26}  {'':>6}  {'':>13}  "
        f"{format_usd(commit_emv_usd, 2):>13}"
    )
    print("-" * len(header))
    for label, probability, value_usd in pilot_outcomes:
        print(
            f"{'PILOT':<8}  {label:<26}  {probability:>6.2f}  "
            f"{format_usd(value_usd, 2):>13}  "
            f"{format_usd(probability * value_usd, 2):>13}"
        )
    print(
        f"{'':<8}  {'EMV (pilot)':<26}  {'':>6}  {'':>13}  "
        f"{format_usd(pilot_emv_usd, 2):>13}"
    )
    print("-" * len(header))
    print()

    print("Comparison")
    print(f"  {'EMV, commit to full build now':<34}{format_usd(commit_emv_usd, 2):>12}")
    print(f"  {'EMV, run a 4-week pilot first':<34}{format_usd(pilot_emv_usd, 2):>12}")
    print(
        f"  {'Difference (pilot - commit)':<34}"
        f"{format_usd(pilot_emv_usd - commit_emv_usd, 2):>12}"
    )
    print()
    print(
        f"Read: the pilot branch carries the higher EMV "
        f"({format_usd(pilot_emv_usd, 2)} vs. {format_usd(commit_emv_usd, 2)}) "
        f"because {format_usd(PILOT_COST_USD)} buys the option to stop before "
        "the full build."
    )
