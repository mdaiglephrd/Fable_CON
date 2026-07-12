-- 0007_research_vocab.sql
-- Seed data for the five research-layer controlled-vocabulary tables.
-- The tables themselves are CREATEd (empty) in 0006 so that FKs in 0006 resolve;
-- their rows are inserted here. Codes are the exact strings from DESIGN.md
-- "RESEARCH LAYER (v2)" and must stay byte-identical to common/vocab.py.
-- migrate.py guarantees run-once, so these are plain INSERTs.

-- Citator treatment (con.vocab_treatment)
INSERT INTO con.vocab_treatment (code)
VALUES
    (N'Followed'),
    (N'Distinguished'),
    (N'Criticized'),
    (N'Reversed'),
    (N'Overruled'),
    (N'Cited'),
    (N'Neutral');

GO

-- Docket family (con.vocab_docket_family)
INSERT INTO con.vocab_docket_family (code)
VALUES
    (N'CON'),
    (N'DET'),
    (N'DET-EQT'),
    (N'DET-ASC'),
    (N'LNR-ASC'),
    (N'LNR-EQT');

GO

-- Docket timeline event type (con.vocab_event_type)
INSERT INTO con.vocab_event_type (code)
VALUES
    (N'Filing'),
    (N'Order'),
    (N'Opinion'),
    (N'Hearing'),
    (N'Brief'),
    (N'Notice');

GO

-- Counsel / party side (con.vocab_counsel_side)
INSERT INTO con.vocab_counsel_side (code)
VALUES
    (N'Applicant'),
    (N'Petitioner'),
    (N'Respondent'),
    (N'Appellant'),
    (N'Appellee'),
    (N'Intervenor'),
    (N'Amicus'),
    (N'Agency');

GO

-- Good-law banner level (con.vocab_treatment_level)
INSERT INTO con.vocab_treatment_level (code)
VALUES
    (N'positive'),
    (N'caution'),
    (N'negative'),
    (N'neutral');

GO
