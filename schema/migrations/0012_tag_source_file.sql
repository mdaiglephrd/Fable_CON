-- 0012_tag_source_file.sql
-- Idempotency ledger for the tag ETL (ingest/tag_orchestrate.py), mirroring
-- the con.processed_blob pattern already used by functions/processing.py:
-- a 'Failed' or 'Unresolved' row does not block reprocessing (only
-- 'Succeeded' does), so a crash mid-run or a later crosswalk improvement can
-- both re-attempt a file safely.
--
-- Keyed by (path_hash, file_hash) rather than the real file_path directly:
-- an on-disk path can be arbitrarily long, and a composite key including it
-- would risk exceeding SQL Server's 900-byte index key limit. Hashing the
-- path first (common/file_identity.py hash_path) keeps the key a fixed,
-- small size while still keying on both dimensions of the file's stable
-- identity (path + content hash) that ingest/tag_load.py's docstring calls
-- for. file_path itself is kept as a plain (unindexed) column for operator
-- readability in the rejects/verification queries.

CREATE TABLE con.tag_source_file (
    path_hash    CHAR(64)       NOT NULL,
    file_hash    CHAR(64)       NOT NULL,
    file_path    NVARCHAR(1000) NOT NULL,
    entry_id     INT            NULL,       -- NULL when the crosswalk did not resolve one
    status       NVARCHAR(20)   NOT NULL,
    detail       NVARCHAR(MAX)  NULL,
    processed_at DATETIME2      NOT NULL CONSTRAINT DF_tag_source_file_processed_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_tag_source_file PRIMARY KEY (path_hash, file_hash),
    CONSTRAINT FK_tag_source_file_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT CK_tag_source_file_status
        CHECK (status IN (N'Succeeded', N'Failed', N'Unresolved'))
);
GO

CREATE INDEX IX_tag_source_file_entry_id ON con.tag_source_file (entry_id);
GO
