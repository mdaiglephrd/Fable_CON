-- 0008a_statute_seed.sql
-- Minimal seed for con.statute (table created in 0006, never seeded since).
-- 0009_deadline_rules.sql's basis_statute FK requires these rows to exist.
--
-- This is scaffolding, not verified legal content: citation_label and kind
-- are filled in so the FK resolves and the citator has something to link to;
-- title/full_text/effective_date/regime_note/subsections_json are left NULL
-- pending human review, same "editorial data, not extraction targets"
-- philosophy docs/05 already applies to headnotes/synopses elsewhere in this
-- schema. Update these rows with verified text once reviewed -- do not treat
-- their current NULL fields as authoritative.

INSERT INTO con.statute (statute_id, kind, citation_label)
VALUES
    (N'31-6-2', N'OCGA', N'O.C.G.A. section 31-6-2'),
    (N'31-6-44', N'OCGA', N'O.C.G.A. section 31-6-44'),
    (N'31-6-44.1', N'OCGA', N'O.C.G.A. section 31-6-44.1'),
    (N'50-13-19', N'OCGA', N'O.C.G.A. section 50-13-19');

GO
