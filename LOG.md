# LabDesk Build Log

Append-only, timestamped. Entry types: **built** / **error-and-fix** / **decision** / **descoped**.

## 2026-09-21 22:40 PDT — Planning frozen; pre-build decisions
- **built**: Execution plan frozen (4-feature Streamlit + SQLite app, seed, pytest, analysis scripts, README). PRINCIPLES.md generated via the coding-principles skill before any code, per Murat's request.
- **decision**: Technicians are a fixed constant list of 3 names in core.py (matching the 3 part-time student techs); the desk lead triages and is not assignable. Simpler alternative to a technicians DB table — no CRUD for techs is needed.
- **decision**: "Open tickets per technician" (workload) counts statuses Open + In Progress, grouped by assignee, with an Unassigned bucket. Rejected: Open-only (undercounts active work).
- **decision**: "Oldest open tickets" = 5 oldest by created_at with status Open or In Progress.
- **decision**: Average time-to-resolution = mean(resolved_at − created_at) over tickets that have resolved_at; Closed preserves resolved_at. Reopen (Resolved→Open) clears resolved_at and keeps the assignee.
- **decision**: Closed is terminal — the spec allows only Resolved→Open as a reopen path, so no Closed→Open.
- **decision**: Timestamps stored as ISO-8601 local-time strings in SQLite text columns. Rejected UTC: single-machine local demo, local times read better in the UI and report.
- **decision**: seed.py resets by dropping and recreating tables with a fixed random seed — idempotent, so re-running is safe by construction.
- **decision**: analysis/monte_carlo.png is committed to the repo so the report figure survives a fresh clone.
- **decision**: Dependencies capped at streamlit, pytest, matplotlib; stdlib random/statistics for all math (no numpy needed at 10,000 trials).

## 2026-09-21 22:41 PDT — Bootstrap review round
- **descoped**: GitHub Actions CI (suggested by the git-workflow reviewer). Rejected because grading is a local fresh-venv cold run, the deadline is ~24h, and the definition of done already requires locally green pytest verified independently before completion. Local verification gates replace CI for this project.
- **decision**: Git execution model — the github-workflow agent reviews and approves git/GitHub operations; the orchestrator executes the approved commands verbatim. Direct-to-main, small conventional commits, no squash, no force-push.
- **decision**: Commit messages carry no AI-attribution trailers, per the user-authored policy embedded in the github-workflow agent's rules (it overrides the generic harness default). AI involvement is disclosed instead in this log and the README's AI-Assisted Development section — disclosure and authorship hygiene are orthogonal.
