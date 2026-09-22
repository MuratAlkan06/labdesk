# LabDesk

A help-desk ticket system for the CMPE Department Lab Support Desk.
SJSU CMPE 165 — Project 1.

## Team members

- Murat Alkan (solo project — design, implementation, testing and written analysis)

## Project description

LabDesk is a small ticket system for the CMPE Department Lab Support Desk, a
support desk staffed by one desk lead and three part-time student lab
technicians. It is a Python web application: a Streamlit front end over a local
SQLite database file, run on one machine from this repository.

Today the desk's requests arrive three different ways — by email to the lead,
by message in the lab Slack channel, and by students walking up to the desk
during office hours. Nothing holds them together, so a request can be answered
twice or not at all, no one can say which problem has been waiting the longest,
and the desk has no record of how long a fix actually takes. LabDesk replaces
those three channels with one queue: requests are submitted through a form,
listed and searched in one place, triaged by assigning a technician and moving
the ticket through a fixed status flow, and summarized on a dashboard.

The dashboard also reports an adoption measure — the share of tickets arriving
through the web form rather than by email or at the desk — because the desk
only benefits if the form actually displaces the old channels. This is a course
prototype: it runs locally for a single user, and it has no login, no email
sending and no outside services.

## Instructions for running the software

Written for macOS with the commands run from a terminal at the repository root
(the folder containing `app.py`). Each step is copy-pasteable as-is.

1. **Prerequisites.** Python 3.10 or newer, with the `python3` command on your
   PATH. Built and tested on Python 3.14.6. Check your version with:

   ```bash
   python3 --version
   ```

2. **Create a virtual environment** in the repository root:

   ```bash
   python3 -m venv .venv
   ```

3. **Install the dependencies** into it:

   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

4. **Create the database and load the sample data.** Run this from the
   repository root — the database path is relative, so `labdesk.db` is written
   into whatever directory you run from:

   ```bash
   .venv/bin/python seed.py
   ```

   It prints `Seeded labdesk.db: 30 tickets, 19 notes.`

5. **Start the application**, also from the repository root:

   ```bash
   .venv/bin/streamlit run app.py --server.address 127.0.0.1
   ```

   The first time Streamlit runs on a machine it asks for an optional email
   address (`Email:`) before starting. Leave it blank and press Enter; the
   server then starts and prints its address:

   ```
   You can now view your Streamlit app in your browser.

   URL: http://127.0.0.1:8501
   ```

   Open that URL in a browser if a tab does not open by itself, and use the
   sidebar to move between Submit Ticket, Queue and Dashboard. Stop the server
   with `Ctrl+C`.

### Running the tests

From the repository root:

```bash
.venv/bin/pytest
```

28 tests cover the logic in `core.py`. Each one builds its own temporary
database, so running the tests never reads or changes your `labdesk.db`.

### Running the analysis scripts

The three scripts behind the written analysis are standalone and print
plain-text tables. Run them from the repository root:

```bash
.venv/bin/python analysis/npv.py
.venv/bin/python analysis/decision_tree.py
.venv/bin/python analysis/monte_carlo.py
```

`npv.py` prints the discounted cash-flow table, the break-even figures and the
payback period; `decision_tree.py` compares the expected value of committing to
the build now against running a pilot first; `monte_carlo.py` runs 10,000 cost
trials from a fixed seed and **overwrites `analysis/monte_carlo.png`** with the
histogram each time it runs.

## Major features

- **Submit** — A form for logging a request: title, description, category,
  priority, source, and requester name and email. Empty or out-of-range values
  are refused with a message naming the field, and every new ticket starts Open
  and unassigned.
- **Queue** — One list of all tickets, newest first, with a case-insensitive
  text search over title and description plus filters for status, priority,
  category and assignee (including an Unassigned bucket); the filters combine,
  and the result count is shown. Opening a ticket shows every field, its
  timestamps and its notes oldest-first.
- **Triage** — From an opened ticket: assign it to one of the three
  technicians, change its status, and add a note. The status flow is guarded —
  Open → In Progress → Resolved → Closed, plus Resolved → Open to reopen a
  ticket that came back — and every other move is rejected on screen with a
  message naming the move and the statuses allowed from the current one. All
  four statuses stay selectable on purpose so that rejection is visible rather
  than hidden.
- **Dashboard** — Ticket counts by status and by priority, open workload per
  technician (Open plus In Progress, with an Unassigned bucket), the five
  oldest tickets still open, the average time to resolution measured from a
  ticket's creation to its resolution, and the adoption metric: the share of
  tickets arriving from each source, which is how the desk sees whether the web
  form is displacing email and walk-ins.

Deliberately absent: any per-technician resolution-time ranking. The dashboard
reports how much open work each technician is carrying, never who resolves
tickets faster — a product decision to keep the metrics about workload
distribution rather than individual speed.

## Required packages and dependencies

`requirements.txt` lists three packages:

| Package | Minimum version | Used for |
|---|---|---|
| streamlit | ≥ 1.52 | the web interface (`app.py`) |
| pytest | ≥ 8.0 | the test suite (`tests/test_core.py`) |
| matplotlib | ≥ 3.9 | the Monte Carlo histogram (`analysis/monte_carlo.py`) |

Everything else the project uses is in the Python standard library: `sqlite3`
for storage, `random` and `statistics` for the analysis math, plus `datetime`,
`math` and `contextlib`.

Installing Streamlit also pulls in its own dependencies — pandas and numpy
among them — but LabDesk imports neither: the tables and charts are fed plain
Python lists and dicts, and Streamlit converts them internally.

## Sample data

`seed.py` fills the database with a demo month of desk traffic so the queue and
dashboard have something to show:

- It resets the database to a known state: each run drops and recreates both
  tables before inserting, so it is safe to re-run at any time and never
  accumulates duplicates.
- It writes 30 tickets spread over the last 30 days, covering every category,
  priority, status and source, with an uneven workload across the three
  technicians and three tickets left unassigned. Ten of them carry technician
  notes, 19 in total.
- The content is hand-written and the random seed is fixed, so every run
  produces the same desk. Ticket ages are counted back from the moment the
  script runs, so the timestamps move with the clock while the data does not.

Re-run it any time the demo data gets messy:

```bash
.venv/bin/python seed.py
```

## AI-Assisted Development

1. **Tools used.** Claude Code (Anthropic) running a set of custom subagents — an orchestrator plus specialists for git workflow, design review, security review and independent verification — with Claude (claude.ai) used for planning, the numerical model and the written analysis.
2. **What the AI helped build.** Essentially all of the code: the data layer and status-transition logic (`core.py`), the seed data, the 28 tests, the Streamlit interface (`app.py`), the three analysis scripts and the histogram, and the first draft of this README. It also ran the review passes: a live browser design review, a security review (parameterized SQL, a dependency audit, binding the demo server to localhost), and an independent verification from a fresh clone.
3. **An example where AI-generated code did not work.** The ticket detail view computed "days open" as now minus creation time for every ticket, including resolved and closed ones, so a ticket fixed in 30 hours showed "Days open: 14.6". All 28 tests passed with the defect in place, because they cover `core.py` and the bug was in the interface layer; it was caught by the design reviewer in a live browser and fixed by branching on `resolved_at` with a `days_to_resolution` helper. Smaller cases are in `LOG.md`: the dashboard bar charts sorted statuses alphabetically instead of Open → In Progress → Resolved → Closed (Vega-Lite's default, fixed with `sort=False`), and the model's own docstrings twice tripped the keyword checks it had been asked to enforce.
4. **An important decision the human made.** The dashboard reports each technician's open workload but never ranks technicians by resolution speed. That is a product and ethics decision about what the metrics should incentivize (Parts E3 and G of the report), made before coding and enforced through verification; the AI would have built whichever was specified. The other human decisions were the fixed four-feature scope — no login, no email, no cloud — and framing the financial analysis as pilot-before-commit.
