# LabDesk Coding Principles

These rules bind every contributor to this repository — Murat and every subagent. The stakes: this project is graded on the principle that "a simple application that works reliably is preferable to an ambitious application that does not work," the prototype is worth 10 of 100 points, and the written analysis is worth 73 — so a broken demo or a wrong analysis number costs far more than any missing nicety. When a rule conflicts with cleverness, the rule wins. When a rule must be broken, the exception is recorded in LOG.md in the same commit.

## 1. Scope law
- Exactly four features exist: **Submit**, **Queue**, **Triage**, **Dashboard**. Every widget, query, and function must trace to one of them. A fifth feature is a defect even when it works.
- Banned by name: **per-technician resolution-time rankings** or any technician speed comparison. The dashboard shows workload (open-ticket counts per technician) — never who resolves fastest. This is a recorded product decision; do not "improve" it back in.
- No authentication, no email, no cloud calls, no LLM/API calls, no background jobs. Grep-gated (§13).

## 2. Status & resolution law — the most important rule in this codebase
- Statuses are exactly the strings `Open`, `In Progress`, `Resolved`, `Closed`, defined once as `core.STATUSES`. No file retypes them as literals; UI reads the constants.
- Legal transitions live in exactly one place, `core.ALLOWED_TRANSITIONS`: Open→In Progress, In Progress→Resolved, Resolved→Closed, Resolved→Open. Every status write goes through `core.change_status()`. An `UPDATE tickets SET status` anywhere outside core.py is a bug even when it happens to work.
- `resolved_at` is written in exactly two places: set when a ticket enters Resolved, cleared on reopen (Resolved→Open). Closing preserves it. Every duration metric derives from `resolved_at − created_at`; nothing else measures resolution.

## 3. Boundary law
- `core.py` is pure logic + `sqlite3` and must import cleanly without Streamlit. `import streamlit` in core.py is banned.
- `app.py` contains zero SQL and no `sqlite3` import; it calls core functions and renders. `seed.py` and tests import core only.
- pytest never touches app.py: the UI is verified by live review, the logic by tests.

## 4. Naming
- Modules by role: `core`, `seed`, `app`, `tests/test_core`, `analysis/*`. No `utils.py`, `helpers.py`, `misc.py`.
- Vocabulary is fixed by the domain: `ticket`, `note`, `technician`, `assignee`, `requester`, `category`, `priority`, `source`, `status`. Code that says "task", "issue", or "user" is using the wrong vocabulary.
- Timestamps end in `_at` and are ISO-8601 local strings: `created_at`, `resolved_at`. A bare `date` or `time` column or variable is a defect.
- Functions are verb-first (`create_ticket`, `list_tickets`, `add_note`, `change_status`, `dashboard_metrics`); predicates read as booleans (`is_valid_transition`).
- Analysis scalars name their meaning and unit: `initial_cost_usd`, `discount_rate` (0–1 float), `p_high_adoption`. Money is US dollars; probabilities are 0–1 floats, printed as percentages only at output.

## 5. Functions & data access
- One responsibility per function; a function that both queries and renders does not exist here (§3).
- Filters are explicit keyword arguments with `None` = "no filter": `list_tickets(search=None, status=None, priority=None, category=None, assignee=None)`. No boolean flag parameters, no filter dicts of unknown keys.
- One connection helper: `core.get_conn(db_path)` with `sqlite3.Row`; every write commits before returning; every caller passes `db_path` so tests use `tmp_path` databases. One `DEFAULT_DB` constant; no other hardcoded paths.
- Wall-clock time is read only inside `core.now_iso()`; nothing else calls `datetime.now()`, so tests can monkeypatch one seam.

## 6. Streamlit rerun discipline
- Streamlit reruns the whole script on every interaction. Every mutation happens in an `st.form` submit or a button branch that calls exactly one core function and then reruns; never mutate as a side effect of rendering.
- `st.session_state` holds one thing: the currently opened ticket id. New keys require a LOG.md justification.
- Every user-visible failure is an `st.error` naming the exact reason — e.g. `Illegal transition: Open → Closed. Allowed: Open → In Progress.` Never a traceback, never silence.
- `st.cache_*` is banned: the dataset is ~30 rows, and stale reads after a triage action are the only thing caching can buy us.

## 7. Errors & validation
- core raises specific exceptions carrying locator data: `TransitionError(ticket_id, from_status, to_status)`; `ValueError` naming the offending field for a bad category/priority/source.
- core is the authority on validity: it rejects empty titles/requester names and non-member category/priority/source values even if the UI already blocked them.
- No bare `except:`. A caught exception is rendered via `st.error` or re-raised with context — never swallowed.
- PII: the schema has no student-ID or password field, and the submit form shows the "do not include student ID numbers or passwords" help text. Requester emails appear nowhere but the ticket record.

## 8. Analysis-numbers law
- The assignment's expected values are the contract: NPV **+3,529** (PV sum 28,529), break-even cost **28,529**, break-even net cash flow **7,887/yr**, payback **2.78 y**; EMV commit **≈ −5,600**, EMV pilot **≈ +117**; Monte Carlo within **±$400 / ±2 pp** of its stated targets. A script that runs but prints different numbers is broken, not "close".
- `random.triangular(low, high, mode)` — mode is the THIRD argument. Every triangular call uses keyword arguments (`random.triangular(low=220, high=380, mode=300)`) so the classic arg-order bug is impossible.
- Every script: parameters in one marked block at the top; seed set as the first executable line of main; runs standalone as `python analysis/<name>.py`; prints aligned plain-text tables paste-able into a report; all printing under `if __name__ == "__main__":`.
- matplotlib uses the Agg backend explicitly; `analysis/monte_carlo.png` is regenerated and re-committed in the same change whenever a parameter changes.

## 9. Testing
- pytest against a real SQLite file in `tmp_path` per test — the database is the thing under test; mocking sqlite is banned. Tests never touch `labdesk.db`.
- Test names state behavior: `test_open_to_closed_is_rejected`, `test_reopen_clears_resolved_at`, not `test_change_status_2`.
- Each graded behavior has a named test: create+read; combined filters + text search; a valid transition; an invalid transition rejected; `resolved_at` set on Resolved; dashboard counts against a known fixture.
- Every bug found during the build gets its fix, a regression test in the same commit, and a LOG.md entry quoting the actual error.
- No sleeps, no network, no time-dependent assertions — inject time via the `now_iso` seam (§5).

## 10. Honesty & LOG.md
- LOG.md is append-only, timestamped, and updated in the same commit as the work it describes. Entry types: **built** / **error-and-fix** (with the verbatim error or wrong output) / **decision** (decision, simpler alternative rejected, why) / **descoped**.
- README claims only what the fresh-venv cold run proves. Forbidden overclaims in any tracked file: "production-ready", "secure", "scalable", "real-time". Grep-gated (§13).
- The README's AI-Assisted Development section remains exactly four numbered placeholders — no agent ever fills it; that content is Murat's.

## 11. Change discipline & git
- Smallest correct diff; no drive-by refactors; no building ahead of the current slice.
- Conventional commits, one meaningful step each, every commit leaves pytest green. Direct-to-main linear history, no squash, no force-push, and every git/GitHub operation passes through github-workflow approval first.

## 12. Dependencies
- `requirements.txt` is exactly: `streamlit`, `pytest`, `matplotlib`. Any addition requires a LOG.md justification in the same commit. Stdlib first: `random` and `statistics` do this project's math — numpy is not needed and not welcome without a logged reason.

## 13. Enforcement map
| Rule | Enforced by |
|---|---|
| Boundary law (§3) | verification-lead greps: `grep -n streamlit core.py` and `grep -nE "sqlite3|SELECT|INSERT INTO|UPDATE " app.py` must be empty |
| Status writes only via `change_status` (§2) | `grep -rn "SET status" --include="*.py" .` matches core.py only + transition tests |
| No rankings (§1) | dashboard inspection by design-reviewer + verification-lead; `grep -in "rank\|leaderboard\|fastest" app.py core.py` empty |
| Exactly four features (§1) | verification-lead feature inventory vs the spec |
| Forbidden overclaims (§10) | `grep -inE "production-ready|secure|scalable|real-time" README.md LOG.md` empty |
| Analysis numbers (§8) | verification-lead runs all three scripts, compares against §8 verbatim |
| Triangular keyword-args (§8) | `grep -n "triangular" analysis/*.py` shows keyword arguments only |
| pytest green per commit (§11) | github-workflow pre-commit check |
| Everything else | implementation-engineer self-check → verification-lead matrix → release-gate-overseer |
