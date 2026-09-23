---
marp: true
theme: default
paginate: true
---

# What Did I Build and Why?

**LabDesk — CMPE 165 Project 1 — Murat Alkan**

- **Problem:** requests scattered across email, Slack and walk-ins — lost requests, zero visibility
- **The desk:** 1 desk lead + 3 part-time student technicians
- **LabDesk:** 4 features — submit, searchable queue, guarded triage, metrics dashboard (Python · Streamlit · SQLite)
- Every request becomes a ticket — **zero lost**
- Measured in the product: **≥60%** via the web form · resolution **under 48h**

<!--
The organization is a fictional CMPE Department Lab Support Desk: one desk lead and three part-time student technicians. A request reaches them three ways — email to the lead, the lab Slack channel, or a student walking up — so there is no single record. The same fix gets done twice or nobody does it, and when the lead is asked which problem has waited longest, the honest answer is that nobody knows. LabDesk replaces those three channels with one queue. Exactly four features, and I froze that count before writing any code: simple and reliable was the explicit strategy, because the grading principle mirrors a real management principle. The two targets that matter live inside the product — at least sixty percent of tickets through the form, and resolution under forty-eight hours.
-->

---

# How Did I Execute?

- **Team:** solo student directing an AI agent team — orchestrator, implementers, design + security reviewers, independent verifier; every change gated
- **Leadership:** servant / situational — behind schedule: **cut scope, never quality** (CI + UI polish descoped; 4 features fixed)
- **Conflict:** desk lead wants per-technician speed rankings; technicians object
- **Settlement:** open workload + team-level resolution time — **no individual rankings**
- **Vibe-coding lesson:** “Days open: 14.6” on a ticket resolved in 30 hours passed **28 green tests** — only a live review caught it

<!--
I was solo, so I ran this as a manager rather than a coder: an orchestrator, implementers, a live design reviewer, a security reviewer and an independent verifier, with every change gated before it landed. When I fell behind I cut scope, never quality — continuous integration and a multi-variant UI exploration went, the four features stayed, and the verification gate was never touched. The conflict I analyzed is the desk lead asking to rank technicians by resolution speed. That number is invalid: ticket difficulty is uneven, it is gameable, and it punishes whoever takes the hard tickets. So I negotiated interests, not positions — open workload per technician, plus one team-level resolution time. And the lesson of the build: a ticket resolved in thirty hours displayed fourteen point six days open, past twenty-eight green tests. Tests were necessary, not sufficient.
-->

---

# What Could Go Wrong?

- Top risks (probability × impact): **Low adoption 20** · **Budget overrun 16** · **Key-person dependency 12**
- Monte Carlo, 10,000 trials: mean cost **$26,734** vs the **$25,000** budget
- P(over budget) = **67.8%**  ·  P80 = **$29,640**
- Decision tree: commit now **EMV = −$5,600** · pilot first **EMV = +$117**

<!--
I scored seven risks on probability times impact. The top three are low adoption at twenty, budget overrun at sixteen, key-person dependency at twelve. Adoption outranks everything technical, and that is the management reading: the dominant risk is not construction, it is that the desk keeps using email. Then I simulated the cost. Ten thousand trials over hours, rate and a rework multiplier put the mean at twenty-six thousand seven hundred against a twenty-five thousand dollar budget, and sixty-seven point eight percent of trials exceed it. A point estimate is not a budget, it is an optimistic sample; the P eighty is twenty-nine thousand six hundred forty. And the decision tree: committing now carries minus five thousand six hundred of expected value, piloting first plus one hundred seventeen. That sign flip prices the option to stop.
-->

---

# Should We Continue?

- Verdict: **GO WITH CONDITIONS**
- Run the 4-week **$2,000** pilot first — **EMV +$117** vs **−$5,600** to commit now
- Commit to the full build only if web-form adoption trends toward **≥60%**
- Budget the full build at P80: **$29,640**, not $25,000
- Keep the **no-rankings** metric policy

<!--
My recommendation is go, with conditions. NPV is positive — plus three thousand five hundred twenty-nine — but thin enough that a cost overrun past twenty-eight and a half thousand erases it, and two independent uncertainties can each do that alone. So the first move is not the build, it is a four-week, two-thousand-dollar pilot: the option to stop is worth more than the commitment, and the tree says so in dollars. I commit the full build only if web-form adoption is trending toward the sixty percent criterion, because that number decides whether the rest matters. I budget at the P eighty, twenty-nine thousand six hundred forty, so the overrun conversation happens now with credibility instead of mid-project without it. And the metric policy holds: workload, not rankings.
-->
