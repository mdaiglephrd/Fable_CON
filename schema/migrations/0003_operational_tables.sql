-- 0003_operational_tables.sql
-- Operational tables: index snapshots, change log, watchlist, weekly report
-- events, processed-blob ledger (DESIGN.md).

CREATE TABLE con.index_snapshot (
    snapshot_id   INT IDENTITY(1,1) NOT NULL,
    blob_name     NVARCHAR(400)     NOT NULL,   -- file or blob name of the .jsonl.gz
    snapshot_date DATE              NULL,
    entry_count   INT               NULL,
    max_entry_id  INT               NULL,
    processed_at  DATETIME2         NOT NULL CONSTRAINT DF_index_snapshot_processed_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_index_snapshot PRIMARY KEY (snapshot_id),
    CONSTRAINT UQ_index_snapshot_blob_name UNIQUE (blob_name)
);
GO

CREATE TABLE con.change_log (
    change_id            BIGINT IDENTITY(1,1) NOT NULL,
    entry_id             INT           NOT NULL,
    change_type          NVARCHAR(10)  NOT NULL,
    old_snapshot_id      INT           NULL,
    new_snapshot_id      INT           NULL,
    details              NVARCHAR(MAX) NULL,   -- {"field": {"old":..., "new":...}} or full record
    in_scope             BIT           NOT NULL CONSTRAINT DF_change_log_in_scope DEFAULT 0,
    revalidation_flagged BIT           NOT NULL CONSTRAINT DF_change_log_revalidation_flagged DEFAULT 0,
    detected_at          DATETIME2     NOT NULL CONSTRAINT DF_change_log_detected_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_change_log PRIMARY KEY (change_id),
    CONSTRAINT FK_change_log_old_snapshot
        FOREIGN KEY (old_snapshot_id) REFERENCES con.index_snapshot (snapshot_id),
    CONSTRAINT FK_change_log_new_snapshot
        FOREIGN KEY (new_snapshot_id) REFERENCES con.index_snapshot (snapshot_id),
    CONSTRAINT CK_change_log_change_type
        CHECK (change_type IN (N'added', N'modified', N'deleted')),
    CONSTRAINT CK_change_log_details_json CHECK (ISJSON(details) = 1)
);
GO

CREATE TABLE con.watchlist (
    watch_id    INT IDENTITY(1,1) NOT NULL,
    docket_id   NVARCHAR(50)  NULL,
    entry_id    INT           NULL,
    path_prefix NVARCHAR(400) NULL,   -- watch new repo docs under a folder path
    reason      NVARCHAR(400) NULL,
    created_by  NVARCHAR(100) NULL,
    active      BIT           NOT NULL CONSTRAINT DF_watchlist_active DEFAULT 1,
    created_at  DATETIME2     NOT NULL CONSTRAINT DF_watchlist_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_watchlist PRIMARY KEY (watch_id),
    CONSTRAINT FK_watchlist_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id)
);
GO

CREATE TABLE con.weekly_report_event (
    event_id            BIGINT IDENTITY(1,1) NOT NULL,
    report_date         DATE          NOT NULL,
    report_file         NVARCHAR(400) NULL,
    section             NVARCHAR(40)  NOT NULL,
    docket_id           NVARCHAR(50)  NULL,   -- canonical; NULL when no docket in the entry
    docket_raw          NVARCHAR(100) NULL,   -- docket exactly as printed
    applicant           NVARCHAR(500) NULL,
    project_description NVARCHAR(MAX) NULL,
    county              NVARCHAR(30)  NULL,
    cost                DECIMAL(18,2) NULL,
    opposition          NVARCHAR(200) NULL,   -- opposition status as printed
    filing_date         DATE          NULL,
    decision_deadline   DATE          NULL,
    decision_date       DATE          NULL,
    raw_text            NVARCHAR(MAX) NULL,
    dedupe_hash         CHAR(64)      NOT NULL,  -- sha256 of (report_date|section|docket_raw|raw_text)
    ingested_at         DATETIME2     NOT NULL CONSTRAINT DF_weekly_report_event_ingested_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_weekly_report_event PRIMARY KEY (event_id),
    CONSTRAINT FK_weekly_report_event_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT CK_weekly_report_event_section
        CHECK (section IN (N'LETTER_OF_INTENT', N'NEW_APPLICATION', N'WITHDRAWN_APPLICATION',
                           N'PENDING_APPLICATION', N'APPROVED', N'DENIED',
                           N'APPEALED', N'LETTER_OF_DETERMINATION')),
    CONSTRAINT UQ_weekly_report_event_dedupe_hash UNIQUE (dedupe_hash)
);
GO

CREATE TABLE con.processed_blob (
    blob_name    NVARCHAR(400) NOT NULL,   -- "container/name"
    processed_at DATETIME2     NOT NULL CONSTRAINT DF_processed_blob_processed_at DEFAULT SYSUTCDATETIME(),
    status       NVARCHAR(20)  NOT NULL,   -- 'succeeded' | 'failed'
    detail       NVARCHAR(MAX) NULL,
    CONSTRAINT PK_processed_blob PRIMARY KEY (blob_name)
);
GO
