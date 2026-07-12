-- 0008_topic_taxonomy.sql
-- Seed the con.topic key-number tree used by the CON research corpus.
-- Roots CON I–VII (parent NULL) are inserted first, then the leaves that the
-- handoff headnotes/citator reference (self-FK con.topic.parent_topic_id
-- requires parents to exist before children). key_number strings use the
-- middle-dot separator "·" exactly as the corpus prints them (e.g. 'CON VI · 24').
-- This seed covers at minimum the ids required by DESIGN.md; extend freely.

-- Roots (parent_topic_id NULL).
INSERT INTO con.topic (topic_id, parent_topic_id, key_number, title, description)
VALUES
    (N'i',   NULL, N'CON I',   N'General Provisions / Scope of Regulation',
        N'Threshold applicability of the CON program and what constitutes a reviewable new institutional health service.'),
    (N'ii',  NULL, N'CON II',  N'Letters of Intent / Filing & Batching',
        N'Letters of intent, application filing, completeness, and comparative batching-cycle review.'),
    (N'iii', NULL, N'CON III', N'Need / Utilization',
        N'Need determinations and utilization thresholds under the CON rules.'),
    (N'iv',  NULL, N'CON IV',  N'Service-Type Need',
        N'Service-specific need methodologies by facility or service type.'),
    (N'v',   NULL, N'CON V',   N'Procedure / Burden of Proof',
        N'Administrative procedure, evidentiary standards, and allocation of the burden of proof.'),
    (N'vi',  NULL, N'CON VI',  N'Judicial Review',
        N'Standard and scope of judicial review of final agency action.'),
    (N'vii', NULL, N'CON VII', N'Remedies / Enforcement',
        N'Remedies, remand, conditions, and enforcement of CON decisions.');

GO

-- Leaves (each with its parent root).
INSERT INTO con.topic (topic_id, parent_topic_id, key_number, title, description)
VALUES
    (N'iii-7',  N'iii', N'CON III · 7',  N'Need / Service-Area Methodology',
        N'Identification of the service area for a need determination, including reliance on demonstrated referral patterns.'),
    (N'iv-11',  N'iv',  N'CON IV · 11',  N'Psychiatric/Behavioral — Need',
        N'Need methodology for psychiatric and behavioral-health beds.'),
    (N'iv-12',  N'iv',  N'CON IV · 12',  N'Hospital Beds — Need',
        N'Need methodology for acute-care hospital beds.'),
    (N'iv-13',  N'iv',  N'CON IV · 13',  N'Ambulatory Surgery — Need',
        N'Need methodology for ambulatory surgery centers.'),
    (N'iv-15',  N'iv',  N'CON IV · 15',  N'Cardiac Cath / OHS — Need',
        N'Need methodology for cardiac catheterization and open-heart surgery services.'),
    (N'v-21',   N'v',   N'CON V · 21',   N'Burden of Proof',
        N'Allocation of the burden of proof on administrative review of a CON decision.'),
    (N'vi-24',  N'vi',  N'CON VI · 24',  N'Substantial Evidence — Standard of Review',
        N'Substantial-evidence standard confining judicial review of a final agency decision.'),
    (N'vi-25',  N'vi',  N'CON VI · 25',  N'Final Agency Action — Remand',
        N'Reversal and remand as the remedy when a final decision rests on an unsupported methodology.');

GO
