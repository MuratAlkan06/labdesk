# LabDesk — Calculation Appendix

CMPE 165 Project 1 · Murat Alkan · Companion to REPORT.md

Every table below is the verbatim output of a deterministic script in `analysis/`. Each runs standalone from the repository root (e.g. `.venv/bin/python analysis/npv.py`); fixed seeds make every number reproducible. Tables and this appendix do not count toward the report word limit.

## Part C — Weighted scoring model (`analysis/weighted_scoring.py`)

```
========================================================================================
LabDesk — Weighted scoring model: project selection
========================================================================================

Candidates
  Project A   LabDesk — help-desk ticket system
  Project B   LabTrack — lab equipment inventory and checkout system

Assumptions
  Raw score scale           1-10, higher is better
  Criterion weights total   100%
  Weighted score (wtd)      weight × raw score
  Project total             sum of the five weighted scores

Criterion                                         Weight   A raw   A wtd   B raw   B wtd
----------------------------------------------------------------------------------------
Strategic alignment with department goals            25%       8    2.00       6    1.50
Financial value (4-year NPV)                         20%       7    1.40       6    1.20
Feasibility within a two-week build                  20%       9    1.80       7    1.40
Adoption likelihood (user willingness to switch)     15%       6    0.90       7    1.05
Operational urgency (severity of current pain)       20%       9    1.80       5    1.00
----------------------------------------------------------------------------------------
Total                                               100%            7.90            6.15

Result
  Project A total      7.90   LabDesk — help-desk ticket system
  Project B total      6.15   LabTrack — lab equipment inventory and checkout system
  Margin (A - B)       1.75

Weighted totals favor Project A, 7.90 vs 6.15.
```

## Part D — Net Present Value (`analysis/npv.py`)

```
==============================================================
LabDesk — Net Present Value
==============================================================

Assumptions
  Initial build cost (year 0)            $25,000
  Annual gross benefit                   $12,000
  Annual maintenance cost                 $3,000
  Annual net cash flow                    $9,000
  Discount rate                            10.0%
  Horizon                                   4 yr

Year     Cash flow   Discount factor   Present value
----------------------------------------------------
   0      -$25,000            1.0000        -$25,000
   1        $9,000            0.9091          $8,182
   2        $9,000            0.8264          $7,438
   3        $9,000            0.7513          $6,762
   4        $9,000            0.6830          $6,147
----------------------------------------------------
 Sum                          3.1699          $3,529

Results
  Present value of benefits (yr 1-4)     $28,529
  Less initial cost                     -$25,000
  Net present value (NPV)                 $3,529

Break-even and payback
  Break-even initial cost                $28,529   (NPV = $0 at this build cost)
  Break-even annual net cash flow         $7,887   (per year, discounted)
  Undiscounted payback period            2.78 yr   (2 years 9 months)

Read: at a 10% discount rate the build returns $3,529 over 4 years.
```

## Part H — Risk register (`analysis/risk_register.py`)

```
===============================================================================================
LabDesk — Risk register (risk score = probability × impact)
===============================================================================================

Assumptions
  P = probability       1-5 ordinal rating, 5 = near certain
  I = impact            1-5 ordinal rating, 5 = project-threatening
  Score = P × I         1-25, ranked descending; ties keep register order
  Coverage              7 risks across 7 categories

Rank  Risk                                                Category          P    I  Score  Note
-----------------------------------------------------------------------------------------------
   1  Low adoption — staff keep using email and Slack     Organizational    4    5     20
   2  Build cost exceeds the $25,000 budget               Financial         4    4     16  [1]
   3  Key-person dependency — one maintainer              Resource          3    4     12
   4  Scope creep from ad-hoc feature requests            Scope             3    3      9
   5  SQLite data loss — no backup routine                Technical         2    4      8
   6  AI-generated code defect ships despite green tests  Quality           3    2      6  [2]
   7  Requester PII mishandled in tickets                 Compliance        2    3      6
-----------------------------------------------------------------------------------------------

Notes
  [1]  Monte Carlo puts P(cost > $25,000) at 67.8%.
  [2]  Occurred once during the build — a UI-layer duration bug all 28 unit tests missed.

Read: the 3 highest-priority risks are low adoption (20), budget overrun (16), and key-person dependency (12).
```

## Part I — Decision tree (`analysis/decision_tree.py`)

```
==================================================================
LabDesk — Decision tree: commit now vs. pilot first
==================================================================

Assumptions
  P(high adoption)                           60%
  P(low adoption)                            40%
  Pilot cost (4 weeks)                    $2,000
  Net cash flow, high adoption            $9,000   per year
  Net cash flow, low adoption             $1,800   per year
  Build NPV, high adoption             $3,528.79
  Build NPV, low adoption            -$19,294.24

Decision  Branch                       Prob.        Outcome   Contribution
--------------------------------------------------------------------------
COMMIT    High adoption                 0.60      $3,528.79      $2,117.27
COMMIT    Low adoption                  0.40    -$19,294.24     -$7,717.70
          EMV (commit)                                          -$5,600.42
--------------------------------------------------------------------------
PILOT     High adoption -> proceed      0.60      $1,528.79        $917.27
PILOT     Low adoption -> stop          0.40     -$2,000.00       -$800.00
          EMV (pilot)                                              $117.27
--------------------------------------------------------------------------

Comparison
  EMV, commit to full build now       -$5,600.42
  EMV, run a 4-week pilot first          $117.27
  Difference (pilot - commit)          $5,717.70

Read: the pilot branch carries the higher EMV ($117.27 vs. -$5,600.42) because $2,000 buys the option to stop before the full build.
```

## Part J — Monte Carlo simulation (`analysis/monte_carlo.py`, seed 42, 10,000 trials)

```
==================================================================
LabDesk — Monte Carlo simulation of total build cost
==================================================================

Assumptions
  Trials                                        10,000
  Random seed                                       42
  Fixed cost                                    $2,500
  Hours (triangular low/mode/high)     220 / 300 / 380
  Hourly rate (uniform low/high)             $65 / $85
  Rework (triangular low/mode/high) 1.00 / 1.03 / 1.20

Statistic                            Value
------------------------------------------
Mean cost                          $26,734
Median cost (P50)                  $26,594
P10 (optimistic)                   $22,413
P80                                $29,640
P90 (pessimistic)                  $31,276
------------------------------------------
P(cost > $25,000)                    67.8%
P(cost > $28,529)                    29.4%
------------------------------------------

Histogram written to analysis/monte_carlo.png

Read: 68% of trials exceed the $25,000 budget and 29% exceed the $28,529 break-even cost. Percentiles use linear interpolation between order statistics.
```

![Monte Carlo cost histogram](analysis/monte_carlo.png)
