-- 0002_core_tables.sql
-- Core tables: con.matter, its child tables, and con.document (DESIGN.md "Core tables").

CREATE TABLE con.matter (
    docket_id            NVARCHAR(50)  NOT NULL,      -- canonical, from common/docket.py
    applicant            NVARCHAR(500) NULL,
    facility             NVARCHAR(500) NULL,
    matter_type          NVARCHAR(60)  NULL,
    action_type          NVARCHAR(60)  NULL,
    county               NVARCHAR(30)  NULL,
    service_area         NVARCHAR(200) NULL,
    bed_count            INT           NULL,
    year_filed           SMALLINT      NULL,
    final_outcome        NVARCHAR(60)  NULL,
    final_decision_date  DATE          NULL,
    highest_review_level TINYINT       NULL,
    completeness_flags   NVARCHAR(MAX) NULL,          -- JSON array of flag strings
    created_at           DATETIME2     NOT NULL CONSTRAINT DF_matter_created_at DEFAULT SYSUTCDATETIME(),
    updated_at           DATETIME2     NOT NULL CONSTRAINT DF_matter_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_matter PRIMARY KEY (docket_id),
    CONSTRAINT FK_matter_matter_type
        FOREIGN KEY (matter_type) REFERENCES con.vocab_matter_type (code),
    CONSTRAINT FK_matter_action_type
        FOREIGN KEY (action_type) REFERENCES con.vocab_action_type (code),
    CONSTRAINT FK_matter_county
        FOREIGN KEY (county) REFERENCES con.county (name),
    CONSTRAINT FK_matter_final_outcome
        FOREIGN KEY (final_outcome) REFERENCES con.vocab_outcome (code),
    CONSTRAINT FK_matter_highest_review_level
        FOREIGN KEY (highest_review_level) REFERENCES con.vocab_decision_level ([level]),
    CONSTRAINT CK_matter_completeness_flags_json CHECK (ISJSON(completeness_flags) = 1)
);
GO

CREATE TABLE con.matter_docket_variant (
    docket_id NVARCHAR(50) NOT NULL,
    variant   NVARCHAR(50) NOT NULL,
    CONSTRAINT PK_matter_docket_variant PRIMARY KEY (docket_id, variant),
    CONSTRAINT FK_matter_docket_variant_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id) ON DELETE CASCADE
);
GO

CREATE TABLE con.matter_service_type (
    docket_id    NVARCHAR(50)  NOT NULL,
    service_type NVARCHAR(100) NOT NULL,
    CONSTRAINT PK_matter_service_type PRIMARY KEY (docket_id, service_type),
    CONSTRAINT FK_matter_service_type_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id) ON DELETE CASCADE,
    CONSTRAINT FK_matter_service_type_vocab
        FOREIGN KEY (service_type) REFERENCES con.vocab_service_type (code)
);
GO

-- phases_present
CREATE TABLE con.matter_phase (
    docket_id NVARCHAR(50) NOT NULL,
    phase     NVARCHAR(80) NOT NULL,
    CONSTRAINT PK_matter_phase PRIMARY KEY (docket_id, phase),
    CONSTRAINT FK_matter_phase_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id) ON DELETE CASCADE,
    CONSTRAINT FK_matter_phase_vocab
        FOREIGN KEY (phase) REFERENCES con.vocab_phase (code)
);
GO

CREATE TABLE con.document (
    entry_id           INT           NOT NULL,        -- Laserfiche Entry ID
    docket_id          NVARCHAR(50)  NULL,
    docview_url        NVARCHAR(400) NULL,
    file_name          NVARCHAR(400) NULL,
    doc_type           NVARCHAR(60)  NULL,
    decision_level     TINYINT       NULL,
    phase              NVARCHAR(80)  NULL,
    page_count         INT           NULL,
    repo_date_created  DATETIME2     NULL,
    repo_date_modified DATETIME2     NULL,
    doc_date           DATE          NULL,
    decision_maker     NVARCHAR(200) NULL,
    outcome            NVARCHAR(60)  NULL,
    parties            NVARCHAR(MAX) NULL,            -- JSON array of party name strings
    source_path        NVARCHAR(1000) NULL,
    template_name      NVARCHAR(200) NULL,
    ocr_status         NVARCHAR(30)  NULL,
    ocr_confidence     DECIMAL(5,2)  NULL,
    validation_status  NVARCHAR(20)  NOT NULL CONSTRAINT DF_document_validation_status DEFAULT N'Unvalidated',
    validated_by       NVARCHAR(100) NULL,
    validated_date     DATETIME2     NULL,
    duplicate_of       INT           NULL,
    created_at         DATETIME2     NOT NULL CONSTRAINT DF_document_created_at DEFAULT SYSUTCDATETIME(),
    updated_at         DATETIME2     NOT NULL CONSTRAINT DF_document_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_document PRIMARY KEY (entry_id),
    CONSTRAINT FK_document_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT FK_document_doc_type
        FOREIGN KEY (doc_type) REFERENCES con.vocab_doc_type (code),
    CONSTRAINT FK_document_decision_level
        FOREIGN KEY (decision_level) REFERENCES con.vocab_decision_level ([level]),
    CONSTRAINT FK_document_phase
        FOREIGN KEY (phase) REFERENCES con.vocab_phase (code),
    CONSTRAINT FK_document_outcome
        FOREIGN KEY (outcome) REFERENCES con.vocab_outcome (code),
    -- Self-referencing FK: SQL Server disallows cascading actions here, so NO ACTION.
    CONSTRAINT FK_document_duplicate_of
        FOREIGN KEY (duplicate_of) REFERENCES con.document (entry_id),
    CONSTRAINT CK_document_parties_json CHECK (ISJSON(parties) = 1),
    CONSTRAINT CK_document_validation_status
        CHECK (validation_status IN (N'Unvalidated', N'Validated', N'Corrected', N'Rejected'))
);
GO
