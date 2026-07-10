# Purview governance for the CON research database

This artifact is a set of governance recommendations, not a paste-in
configuration: see **[governance.md](governance.md)** for the full guide.

It covers, per capability and using only what Microsoft 365 E7 includes:

1. **Sensitivity labels** — a public-record label for CON data, a separate
   confidential label for analyst notes, and auto-labeling via a custom
   docket-ID sensitive information type.
2. **Data loss prevention** — deliberately light for public-record data; where
   DLP does apply (analyst annotations, agent interactions).
3. **Records management** — retention labels per record class, with the
   explicit instruction to confirm periods against the Georgia Archives
   retention schedules (none are invented here).
4. **Data Map / Unified Catalog** — registering and scanning the Azure SQL
   database.
5. **Audit** — Purview Audit plus Azure SQL auditing for the Power App
   validation actions.
6. **AI-agent governance** — DSPM for AI, Communication Compliance, Agent 365,
   and the Defender-for-AI angle for the Copilot Studio agent.

Each section in governance.md states **What to configure**, **Exact steps**,
and **E7 coverage** (covered vs extra cost).
