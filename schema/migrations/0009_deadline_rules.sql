-- 0009_deadline_rules.sql
-- Seed data for con.deadline_rule (table + con schema created by 0006).
-- These rows are generated from common/deadline_rules.py DEADLINE_RULES and
-- must stay byte-identical to that constant (single source of truth for the
-- /deadlines/calculate endpoint). migrate.py guarantees run-once, so this is a
-- plain INSERT batch.

INSERT INTO con.deadline_rule
    (rule_id, docket_family, trigger_event, offset_days, basis_statute, description)
VALUES
    (N'con-challenge-window', N'CON', N'Letter of determination', 30, N'31-6-44',
        N'Request for an administrative hearing (challenge) is due within 30 days of the letter of determination.'),
    (N'con-ho-appointment', N'CON', N'Challenge filed', 30, N'31-6-44',
        N'Hearing officer appointment is due within 30 days of the challenge.'),
    (N'con-hearing-window-open', N'CON', N'Hearing officer appointed', 60, N'31-6-44',
        N'Hearing window opens 60 days after the hearing officer appointment.'),
    (N'con-hearing-window-close', N'CON', N'Hearing officer appointed', 120, N'31-6-44',
        N'Hearing window closes 120 days after the hearing officer appointment.'),
    (N'con-ho-decision', N'CON', N'Hearing concluded', 30, N'31-6-44',
        N'Hearing officer decision is due within 30 days of hearing conclusion.'),
    (N'con-judicial-petition', N'CON', N'Final agency decision', 30, N'31-6-44.1',
        N'Petition for judicial review is due within 30 days of the final agency decision.'),
    (N'con-finality-default', N'CON', N'Superior court docketing', 120, N'50-13-19',
        N'120-day default: if the superior court does not hear the case within 120 days of docketing, the agency decision is affirmed by operation of law (O.C.G.A. § 50-13-19, as modified by § 31-6-44.1).'),
    (N'det-sufficiency', N'DET', N'Request filed', 11, N'31-6-2',
        N'Sufficiency screen (administrative, informational) — opens the ~60-day review window.'),
    (N'det-letter', N'DET', N'Request filed', 60, N'31-6-2',
        N'Letter of determination is due ~60 days from filing.'),
    (N'det-challenge-window', N'DET', N'Letter of determination', 30, N'31-6-44',
        N'Challenge (request for an administrative hearing) is due within 30 days of the letter of determination.'),
    (N'det-ho-appointment', N'DET', N'Challenge filed', 30, N'31-6-44',
        N'Hearing officer appointment is due within 30 days of the appeal — same mechanics as the CON administrative appeal.'),
    (N'det-hearing-window-open', N'DET', N'Hearing officer appointed', 60, N'31-6-44',
        N'Hearing window opens 60 days after appointment — same mechanics as CON.'),
    (N'det-hearing-window-close', N'DET', N'Hearing officer appointed', 120, N'31-6-44',
        N'Hearing window closes 120 days after appointment — same mechanics as CON.'),
    (N'det-ho-decision', N'DET', N'Hearing concluded', 30, N'31-6-44',
        N'Hearing officer decision is due within 30 days of hearing conclusion; under HB 1339 the HO decision is the final agency decision.'),
    (N'det-judicial-petition', N'DET', N'Final agency decision', 30, N'31-6-44.1',
        N'Petition for judicial review is due within 30 days of the final agency decision.'),
    (N'det-finality-default', N'DET', N'Superior court docketing', 120, N'50-13-19',
        N'120-day default finality on judicial review (O.C.G.A. § 50-13-19, as modified by § 31-6-44.1).');

GO
