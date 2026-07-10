-- 0005_fulltext.sql
-- Full-text catalog and indexes (DESIGN.md "Full-text search").
--
-- This file is applied with autocommit (CREATE FULLTEXT INDEX cannot run inside
-- a user transaction) and can be skipped with `python -m schema.migrate
-- --skip-fulltext` on environments without full-text support (localdev/tests).
-- The KEY INDEX names below are the explicit PK constraint names from
-- 0002_core_tables.sql / 0003_operational_tables.sql.

CREATE FULLTEXT CATALOG con_fts;
GO

CREATE FULLTEXT INDEX ON con.matter
    (
        applicant    LANGUAGE 1033,
        facility     LANGUAGE 1033,
        service_area LANGUAGE 1033
    )
    KEY INDEX PK_matter ON con_fts
    WITH CHANGE_TRACKING AUTO;
GO

CREATE FULLTEXT INDEX ON con.document
    (
        file_name      LANGUAGE 1033,
        decision_maker LANGUAGE 1033,
        source_path    LANGUAGE 1033
    )
    KEY INDEX PK_document ON con_fts
    WITH CHANGE_TRACKING AUTO;
GO

CREATE FULLTEXT INDEX ON con.weekly_report_event
    (
        applicant           LANGUAGE 1033,
        project_description LANGUAGE 1033
    )
    KEY INDEX PK_weekly_report_event ON con_fts
    WITH CHANGE_TRACKING AUTO;
GO
