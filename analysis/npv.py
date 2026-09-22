"""LabDesk analysis — net present value of building the lab support desk.

Standalone standard-library script (PRINCIPLES.md §8). Run from the repository
root:

    .venv/bin/python analysis/npv.py

Discounts four years of net benefit at 10 percent, then reports the two
break-even figures and the undiscounted payback period. There is no randomness
here, so there is no seed. Every figure is computed in full precision and
rounded only at print time, and all printing lives under the ``__main__``
guard so the module stays silent on import.
"""

import math

# --- Parameters (the only numbers to edit; PRINCIPLES.md §8) -----------------

INITIAL_COST_USD = 25_000
ANNUAL_GROSS_BENEFIT_USD = 12_000
ANNUAL_MAINTENANCE_USD = 3_000
DISCOUNT_RATE = 0.10
YEARS = 4

# --- End of parameters -------------------------------------------------------

# Derived from the parameters above, not a knob of its own: what the desk
# actually nets each year after paying to keep it running.
ANNUAL_NET_CASH_FLOW_USD = ANNUAL_GROSS_BENEFIT_USD - ANNUAL_MAINTENANCE_USD


def format_usd(amount_usd, decimals=0):
    """Format dollars with a thousands separator, e.g. ``-$25,000``."""
    sign = "-" if amount_usd < 0 else ""
    return f"{sign}${abs(amount_usd):,.{decimals}f}"


def discount_factor(discount_rate, year):
    """Present value of one dollar received ``year`` years from now."""
    return 1.0 / ((1.0 + discount_rate) ** year)


def annuity_factor(discount_rate, years):
    """Sum of the discount factors for years 1..``years`` (≈3.169865 here)."""
    return sum(discount_factor(discount_rate, year) for year in range(1, years + 1))


def present_value_of_annuity(annual_cash_flow_usd, discount_rate, years):
    """Present value of an equal cash flow received at the end of each year."""
    return annual_cash_flow_usd * annuity_factor(discount_rate, years)


def net_present_value(initial_cost_usd, annual_cash_flow_usd, discount_rate, years):
    """NPV of paying ``initial_cost_usd`` now for a level annual cash flow."""
    pv_sum_usd = present_value_of_annuity(annual_cash_flow_usd, discount_rate, years)
    return pv_sum_usd - initial_cost_usd


def break_even_annual_cash_flow(initial_cost_usd, discount_rate, years):
    """Annual net cash flow whose present value exactly repays the build."""
    return initial_cost_usd / annuity_factor(discount_rate, years)


def payback_years(initial_cost_usd, annual_cash_flow_usd):
    """Undiscounted payback period in years (the simple cost/benefit ratio)."""
    return initial_cost_usd / annual_cash_flow_usd


def format_years_and_months(years):
    """Render a fractional year count as e.g. ``2 years 9 months``."""
    whole_years = math.floor(years)
    months = round((years - whole_years) * 12)
    # A fraction that rounds up to a full 12 months belongs to the next year.
    if months == 12:
        whole_years += 1
        months = 0
    year_label = "year" if whole_years == 1 else "years"
    month_label = "month" if months == 1 else "months"
    return f"{whole_years} {year_label} {months} {month_label}"


def cash_flow_schedule(initial_cost_usd, annual_cash_flow_usd, discount_rate, years):
    """Rows of ``(year, cash flow, discount factor, present value)``.

    Year 0 carries the build cost as a negative flow at a discount factor of
    1.0; years 1..``years`` carry the level net benefit.
    """
    rows = [(0, -initial_cost_usd, 1.0, -initial_cost_usd)]
    for year in range(1, years + 1):
        factor = discount_factor(discount_rate, year)
        rows.append((year, annual_cash_flow_usd, factor, annual_cash_flow_usd * factor))
    return rows


if __name__ == "__main__":
    schedule = cash_flow_schedule(
        INITIAL_COST_USD, ANNUAL_NET_CASH_FLOW_USD, DISCOUNT_RATE, YEARS
    )
    pv_sum_usd = present_value_of_annuity(
        ANNUAL_NET_CASH_FLOW_USD, DISCOUNT_RATE, YEARS
    )
    npv_usd = net_present_value(
        INITIAL_COST_USD, ANNUAL_NET_CASH_FLOW_USD, DISCOUNT_RATE, YEARS
    )
    factor_sum = annuity_factor(DISCOUNT_RATE, YEARS)
    break_even_cost_usd = pv_sum_usd
    break_even_cash_flow_usd = break_even_annual_cash_flow(
        INITIAL_COST_USD, DISCOUNT_RATE, YEARS
    )
    payback = payback_years(INITIAL_COST_USD, ANNUAL_NET_CASH_FLOW_USD)

    print("=" * 62)
    print("LabDesk — Net Present Value")
    print("=" * 62)
    print()
    print("Assumptions")
    print(f"  {'Initial build cost (year 0)':<34}{format_usd(INITIAL_COST_USD):>12}")
    print(
        f"  {'Annual gross benefit':<34}"
        f"{format_usd(ANNUAL_GROSS_BENEFIT_USD):>12}"
    )
    print(
        f"  {'Annual maintenance cost':<34}"
        f"{format_usd(ANNUAL_MAINTENANCE_USD):>12}"
    )
    print(
        f"  {'Annual net cash flow':<34}"
        f"{format_usd(ANNUAL_NET_CASH_FLOW_USD):>12}"
    )
    print(f"  {'Discount rate':<34}{DISCOUNT_RATE * 100:>11.1f}%")
    print(f"  {'Horizon':<34}{YEARS:>9} yr")
    print()

    header = f"{'Year':>4}  {'Cash flow':>12}  {'Discount factor':>16}  {'Present value':>14}"
    print(header)
    print("-" * len(header))
    for year, cash_flow_usd, factor, present_value_usd in schedule:
        print(
            f"{year:>4}  {format_usd(cash_flow_usd):>12}  {factor:>16.4f}  "
            f"{format_usd(present_value_usd):>14}"
        )
    print("-" * len(header))
    print(
        f"{'Sum':>4}  {'':>12}  {factor_sum:>16.4f}  "
        f"{format_usd(pv_sum_usd - INITIAL_COST_USD):>14}"
    )
    print()

    print("Results")
    print(f"  {'Present value of benefits (yr 1-4)':<34}{format_usd(pv_sum_usd):>12}")
    print(f"  {'Less initial cost':<34}{format_usd(-INITIAL_COST_USD):>12}")
    print(f"  {'Net present value (NPV)':<34}{format_usd(npv_usd):>12}")
    print()

    print("Break-even and payback")
    print(
        f"  {'Break-even initial cost':<34}{format_usd(break_even_cost_usd):>12}"
        "   (NPV = $0 at this build cost)"
    )
    print(
        f"  {'Break-even annual net cash flow':<34}"
        f"{format_usd(break_even_cash_flow_usd):>12}"
        "   (per year, discounted)"
    )
    print(
        f"  {'Undiscounted payback period':<34}{payback:>9.2f} yr"
        f"   ({format_years_and_months(payback)})"
    )
    print()
    print(
        f"Read: at a {DISCOUNT_RATE * 100:.0f}% discount rate the build returns "
        f"{format_usd(npv_usd)} over {YEARS} years."
    )
