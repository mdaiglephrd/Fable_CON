-- 0004_indexes.sql
-- Nonclustered indexes beyond primary keys (DESIGN.md "Indexes").

-- document: (docket_id), (doc_type), (phase), (outcome), (validation_status), (doc_date)
CREATE NONCLUSTERED INDEX IX_document_docket_id         ON con.document (docket_id);
CREATE NONCLUSTERED INDEX IX_document_doc_type          ON con.document (doc_type);
CREATE NONCLUSTERED INDEX IX_document_phase             ON con.document (phase);
CREATE NONCLUSTERED INDEX IX_document_outcome           ON con.document (outcome);
CREATE NONCLUSTERED INDEX IX_document_validation_status ON con.document (validation_status);
CREATE NONCLUSTERED INDEX IX_document_doc_date          ON con.document (doc_date);
GO

-- matter: (county), (year_filed), (final_outcome), (matter_type), (action_type)
CREATE NONCLUSTERED INDEX IX_matter_county        ON con.matter (county);
CREATE NONCLUSTERED INDEX IX_matter_year_filed    ON con.matter (year_filed);
CREATE NONCLUSTERED INDEX IX_matter_final_outcome ON con.matter (final_outcome);
CREATE NONCLUSTERED INDEX IX_matter_matter_type   ON con.matter (matter_type);
CREATE NONCLUSTERED INDEX IX_matter_action_type   ON con.matter (action_type);
GO

-- matter_service_type: (service_type)
CREATE NONCLUSTERED INDEX IX_matter_service_type_service_type ON con.matter_service_type (service_type);
GO

-- matter_docket_variant: (variant) — docket resolution looks up by variant string
CREATE NONCLUSTERED INDEX IX_matter_docket_variant_variant ON con.matter_docket_variant (variant);
GO

-- change_log: (entry_id), (detected_at), (change_type)
CREATE NONCLUSTERED INDEX IX_change_log_entry_id    ON con.change_log (entry_id);
CREATE NONCLUSTERED INDEX IX_change_log_detected_at ON con.change_log (detected_at);
CREATE NONCLUSTERED INDEX IX_change_log_change_type ON con.change_log (change_type);
GO

-- weekly_report_event: (docket_id), (report_date), (section)
CREATE NONCLUSTERED INDEX IX_weekly_report_event_docket_id   ON con.weekly_report_event (docket_id);
CREATE NONCLUSTERED INDEX IX_weekly_report_event_report_date ON con.weekly_report_event (report_date);
CREATE NONCLUSTERED INDEX IX_weekly_report_event_section     ON con.weekly_report_event (section);
GO
