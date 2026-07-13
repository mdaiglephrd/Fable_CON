-- 0011_axis_tag_tables.sql
-- Tag-assignment structures for the Georgia CON Tagging Taxonomy. These stay
-- empty after the Phase 1 ETL (ingest/tag_orchestrate.py) loads document
-- records -- Phase 2 (a human, via Harvey Vaults/Review Tables, through
-- ingest/load_axis_tags.py) is what populates them. See docs/08-harvey-
-- tagging-guide.md.
--
-- Axis 1 & 2 are single-value per document (PK on entry_id alone). Axis 3 & 4
-- are multi-value (PK on entry_id + code; zero or more rows per document).
--
-- Masterfile rule: a document tagged Masterfile on Axis 2 must carry no Axis
-- 3/4 tags. This is enforced here with triggers (not just documented as a
-- convention) in both directions, so neither write order can create the
-- invalid state:
--   trg_axis2_masterfile_guard   -- blocks tagging Masterfile while Axis 3/4 rows exist
--   trg_axis3_masterfile_guard   -- blocks adding an Axis 3 row to a Masterfile-tagged document
--   trg_axis4_masterfile_guard   -- same, for Axis 4
-- The same rule is also enforced in Python (common/axis_validation.py) so
-- ingest/load_axis_tags.py can reject bad rows into a --rejects report before
-- ever reaching these triggers.

CREATE TABLE con.document_axis1 (
    entry_id INT          NOT NULL,
    value    NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_document_axis1 PRIMARY KEY (entry_id),
    CONSTRAINT FK_document_axis1_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_document_axis1_vocab
        FOREIGN KEY (value) REFERENCES con.vocab_axis1_proceeding_type (code)
);
GO

CREATE TABLE con.document_axis2 (
    entry_id INT          NOT NULL,
    value    NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_document_axis2 PRIMARY KEY (entry_id),
    CONSTRAINT FK_document_axis2_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_document_axis2_vocab
        FOREIGN KEY (value) REFERENCES con.vocab_axis2_authority_type (code)
);
GO

CREATE TABLE con.document_axis3 (
    entry_id INT          NOT NULL,
    code     NVARCHAR(10) NOT NULL,
    CONSTRAINT PK_document_axis3 PRIMARY KEY (entry_id, code),
    CONSTRAINT FK_document_axis3_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_document_axis3_vocab
        FOREIGN KEY (code) REFERENCES con.axis3_substantive_issue (code)
);
GO

CREATE TABLE con.document_axis4 (
    entry_id INT          NOT NULL,
    code     NVARCHAR(10) NOT NULL,
    CONSTRAINT PK_document_axis4 PRIMARY KEY (entry_id, code),
    CONSTRAINT FK_document_axis4_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_document_axis4_vocab
        FOREIGN KEY (code) REFERENCES con.axis4_procedural_issue (code)
);
GO

-- ---------------------------------------------------------------------------
-- Masterfile constraint triggers
-- ---------------------------------------------------------------------------

CREATE TRIGGER con.trg_axis2_masterfile_guard
ON con.document_axis2
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        WHERE i.value = N'Masterfile'
          AND (
              EXISTS (SELECT 1 FROM con.document_axis3 a3 WHERE a3.entry_id = i.entry_id)
              OR EXISTS (SELECT 1 FROM con.document_axis4 a4 WHERE a4.entry_id = i.entry_id)
          )
    )
    BEGIN
        RAISERROR (
            'Cannot tag entry_id as Masterfile (Axis 2) while Axis 3/4 tags exist; remove them first.',
            16, 1);
        ROLLBACK TRANSACTION;
    END
END
GO

CREATE TRIGGER con.trg_axis3_masterfile_guard
ON con.document_axis3
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN con.document_axis2 a2 ON a2.entry_id = i.entry_id
        WHERE a2.value = N'Masterfile'
    )
    BEGIN
        RAISERROR (
            'Cannot add an Axis 3 tag to entry_id tagged Masterfile on Axis 2.',
            16, 1);
        ROLLBACK TRANSACTION;
    END
END
GO

CREATE TRIGGER con.trg_axis4_masterfile_guard
ON con.document_axis4
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN con.document_axis2 a2 ON a2.entry_id = i.entry_id
        WHERE a2.value = N'Masterfile'
    )
    BEGIN
        RAISERROR (
            'Cannot add an Axis 4 tag to entry_id tagged Masterfile on Axis 2.',
            16, 1);
        ROLLBACK TRANSACTION;
    END
END
GO

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IX_document_axis3_code ON con.document_axis3 (code);
GO
CREATE INDEX IX_document_axis4_code ON con.document_axis4 (code);
GO
