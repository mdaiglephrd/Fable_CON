-- 0006_research_tables.sql
-- Research layer (v2) — additive tables on top of the v1 inventory.
-- DESIGN.md "RESEARCH LAYER (v2)" is authoritative for every name, type, FK,
-- CHECK and index below.
--
-- Ordering note: migrations run in filename order, so 0006 runs BEFORE 0007.
-- Several v2 tables here FK to the five new controlled-vocabulary tables
-- (vocab_treatment, vocab_docket_family, vocab_event_type, vocab_counsel_side,
-- vocab_treatment_level). To keep those FK targets present we CREATE the vocab
-- tables (empty) HERE in 0006, and SEED their rows in 0007. This mirrors the v1
-- split only in reverse: structure in the earlier file, data in the later one.
--
-- Tables are created so every FK target exists first:
--   vocab tables -> topic / statute -> content/citator -> people/timeline ->
--   statute_xref -> wiki -> projects -> alerts -> deadline_rule -> indexes.
-- Self-referencing FKs (topic.parent_topic_id, statute_xref) use NO ACTION
-- because SQL Server forbids cascading actions that could form a cycle.

-- ---------------------------------------------------------------------------
-- New controlled-vocabulary tables (structure only; seeded in 0007).
-- ---------------------------------------------------------------------------

CREATE TABLE con.vocab_treatment (
    code NVARCHAR(40) NOT NULL,
    CONSTRAINT PK_vocab_treatment PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_docket_family (
    code NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_vocab_docket_family PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_event_type (
    code NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_vocab_event_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_counsel_side (
    code NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_vocab_counsel_side PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_treatment_level (
    code NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_vocab_treatment_level PRIMARY KEY (code)
);
GO

-- ---------------------------------------------------------------------------
-- Extend existing v1 tables (ALTER ... ADD; every new column NULLable).
-- ---------------------------------------------------------------------------

ALTER TABLE con.matter ADD
    contact_officer       NVARCHAR(200) NULL,
    project_description    NVARCHAR(MAX) NULL,
    estimated_cost         DECIMAL(18,2) NULL,
    primary_service_area   NVARCHAR(MAX) NULL,   -- JSON array of counties
    docket_family          NVARCHAR(20)  NULL,
    letter_of_intent_date  DATE          NULL,
    deemed_complete_date   DATE          NULL,
    decision_deadline      DATE          NULL,
    batching_cycle         NVARCHAR(60)  NULL,
    competing_docket_ids   NVARCHAR(MAX) NULL,   -- JSON array of docket ids
    -- valid|questioned|overturned|noprecedent. Reserved for a future write-back job;
    -- today common/proceeding.py computes the equivalent signal on read, so this column
    -- stays NULL unless something explicitly populates it. See docs/05 "precedent_signal".
    precedent_signal       NVARCHAR(20)  NULL;
GO

ALTER TABLE con.matter ADD
    CONSTRAINT FK_matter_docket_family
        FOREIGN KEY (docket_family) REFERENCES con.vocab_docket_family (code),
    CONSTRAINT CK_matter_primary_service_area_json CHECK (ISJSON(primary_service_area) = 1),
    CONSTRAINT CK_matter_competing_docket_ids_json CHECK (ISJSON(competing_docket_ids) = 1),
    CONSTRAINT CK_matter_precedent_signal
        CHECK (precedent_signal IN (N'valid', N'questioned', N'overturned', N'noprecedent'));
GO

ALTER TABLE con.document ADD
    title       NVARCHAR(500) NULL,
    text_source NVARCHAR(10)  NULL;   -- ocr|native|tag
GO

ALTER TABLE con.document ADD
    CONSTRAINT CK_document_text_source
        CHECK (text_source IN (N'ocr', N'native', N'tag'));
GO

-- ---------------------------------------------------------------------------
-- Taxonomy + statutes (FK targets for content/citator tables below).
-- ---------------------------------------------------------------------------

-- Topic tree (self-referencing parent; seeded in 0008). Self-FK is NO ACTION.
CREATE TABLE con.topic (
    topic_id        NVARCHAR(40)  NOT NULL,
    parent_topic_id NVARCHAR(40)  NULL,
    key_number      NVARCHAR(40)  NULL,   -- e.g. 'CON VI · 24'
    title           NVARCHAR(200) NULL,
    description     NVARCHAR(MAX) NULL,
    CONSTRAINT PK_topic PRIMARY KEY (topic_id),
    CONSTRAINT FK_topic_parent
        FOREIGN KEY (parent_topic_id) REFERENCES con.topic (topic_id)
);
GO

CREATE TABLE con.statute (
    statute_id       NVARCHAR(40)  NOT NULL,
    kind             NVARCHAR(10)  NULL,   -- OCGA|RULE
    citation_label   NVARCHAR(200) NULL,
    title            NVARCHAR(400) NULL,
    full_text        NVARCHAR(MAX) NULL,
    effective_date   DATE          NULL,
    regime_note      NVARCHAR(MAX) NULL,
    subsections_json NVARCHAR(MAX) NULL,
    CONSTRAINT PK_statute PRIMARY KEY (statute_id),
    CONSTRAINT CK_statute_kind CHECK (kind IN (N'OCGA', N'RULE')),
    CONSTRAINT CK_statute_subsections_json CHECK (ISJSON(subsections_json) = 1)
);
GO

-- ---------------------------------------------------------------------------
-- Content tables (per document/opinion).
-- ---------------------------------------------------------------------------

CREATE TABLE con.document_text (
    entry_id      INT           NOT NULL,
    full_text     NVARCHAR(MAX) NULL,
    text_source   NVARCHAR(10)  NULL,   -- ocr|native|tag
    char_count    INT           NULL,
    di_model      NVARCHAR(60)  NULL,
    di_confidence DECIMAL(5,2)  NULL,
    extracted_at  DATETIME2     NOT NULL CONSTRAINT DF_document_text_extracted_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_document_text PRIMARY KEY (entry_id),
    CONSTRAINT FK_document_text_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT CK_document_text_text_source
        CHECK (text_source IN (N'ocr', N'native', N'tag'))
);
GO

CREATE TABLE con.opinion (
    entry_id            INT           NOT NULL,
    caption_json        NVARCHAR(MAX) NULL,
    tribunal_line       NVARCHAR(400) NULL,
    byline              NVARCHAR(200) NULL,
    intro_text          NVARCHAR(MAX) NULL,
    disposition_json    NVARCHAR(MAX) NULL,
    editorial_synopsis  NVARCHAR(MAX) NULL,
    decided_date        DATE          NULL,
    argued_date         DATE          NULL,
    court_docket_no     NVARCHAR(60)  NULL,
    subsequent_history  NVARCHAR(MAX) NULL,
    is_published        BIT           NULL,
    standard_of_review  NVARCHAR(200) NULL,
    treatment_level     NVARCHAR(20)  NULL,
    treatment_note_json NVARCHAR(MAX) NULL,
    CONSTRAINT PK_opinion PRIMARY KEY (entry_id),
    CONSTRAINT FK_opinion_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_opinion_treatment_level
        FOREIGN KEY (treatment_level) REFERENCES con.vocab_treatment_level (code),
    CONSTRAINT CK_opinion_caption_json CHECK (ISJSON(caption_json) = 1),
    CONSTRAINT CK_opinion_disposition_json CHECK (ISJSON(disposition_json) = 1),
    CONSTRAINT CK_opinion_treatment_note_json CHECK (ISJSON(treatment_note_json) = 1)
);
GO

CREATE TABLE con.opinion_paragraph (
    paragraph_id BIGINT IDENTITY(1,1) NOT NULL,
    entry_id     INT           NOT NULL,
    para_num     NVARCHAR(10)  NULL,
    segs_json    NVARCHAR(MAX) NULL,   -- tagged-tuple rich-text array
    plain_text   NVARCHAR(MAX) NULL,
    sort_order   INT           NULL,
    CONSTRAINT PK_opinion_paragraph PRIMARY KEY (paragraph_id),
    CONSTRAINT FK_opinion_paragraph_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT CK_opinion_paragraph_segs_json CHECK (ISJSON(segs_json) = 1)
);
GO

CREATE TABLE con.reporter_citation (
    cite_id     BIGINT IDENTITY(1,1) NOT NULL,
    entry_id    INT           NOT NULL,
    citation    NVARCHAR(120) NULL,
    reporter    NVARCHAR(40)  NULL,
    volume      NVARCHAR(20)  NULL,
    page        NVARCHAR(20)  NULL,
    is_parallel BIT           NOT NULL CONSTRAINT DF_reporter_citation_is_parallel DEFAULT 0,
    CONSTRAINT PK_reporter_citation PRIMARY KEY (cite_id),
    CONSTRAINT FK_reporter_citation_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id)
);
GO

CREATE TABLE con.headnote (
    headnote_id BIGINT IDENTITY(1,1) NOT NULL,
    entry_id    INT           NOT NULL,
    num         NVARCHAR(10)  NULL,
    topic_id    NVARCHAR(40)  NULL,
    topic_label NVARCHAR(200) NULL,
    [text]      NVARCHAR(MAX) NULL,
    CONSTRAINT PK_headnote PRIMARY KEY (headnote_id),
    CONSTRAINT FK_headnote_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_headnote_topic
        FOREIGN KEY (topic_id) REFERENCES con.topic (topic_id)
);
GO

-- ---------------------------------------------------------------------------
-- Topic assignment + citator.
-- ---------------------------------------------------------------------------

CREATE TABLE con.document_topic (
    entry_id INT          NOT NULL,
    topic_id NVARCHAR(40) NOT NULL,
    CONSTRAINT PK_document_topic PRIMARY KEY (entry_id, topic_id),
    CONSTRAINT FK_document_topic_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_document_topic_topic
        FOREIGN KEY (topic_id) REFERENCES con.topic (topic_id)
);
GO

-- how-cited = WHERE cited_*; table-of-authorities = WHERE citing_entry_id.
CREATE TABLE con.citation (
    citation_id      BIGINT IDENTITY(1,1) NOT NULL,
    citing_entry_id  INT           NOT NULL,
    cited_entry_id   INT           NULL,
    cited_statute_id NVARCHAR(40)  NULL,
    cited_external   NVARCHAR(300) NULL,
    treatment        NVARCHAR(40)  NULL,
    depth            TINYINT       NULL,
    pinpoint         NVARCHAR(60)  NULL,
    snippet          NVARCHAR(MAX) NULL,
    topic_id         NVARCHAR(40)  NULL,
    CONSTRAINT PK_citation PRIMARY KEY (citation_id),
    CONSTRAINT FK_citation_citing_document
        FOREIGN KEY (citing_entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_citation_cited_document
        FOREIGN KEY (cited_entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_citation_cited_statute
        FOREIGN KEY (cited_statute_id) REFERENCES con.statute (statute_id),
    CONSTRAINT FK_citation_treatment
        FOREIGN KEY (treatment) REFERENCES con.vocab_treatment (code),
    CONSTRAINT FK_citation_topic
        FOREIGN KEY (topic_id) REFERENCES con.topic (topic_id)
);
GO

-- ---------------------------------------------------------------------------
-- People / filings / timeline.
-- ---------------------------------------------------------------------------

CREATE TABLE con.counsel (
    counsel_id    BIGINT IDENTITY(1,1) NOT NULL,
    entry_id      INT           NULL,
    docket_id     NVARCHAR(50)  NULL,
    role          NVARCHAR(120) NULL,
    attorney_name NVARCHAR(200) NULL,
    firm          NVARCHAR(200) NULL,
    party_side    NVARCHAR(20)  NULL,
    CONSTRAINT PK_counsel PRIMARY KEY (counsel_id),
    CONSTRAINT FK_counsel_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_counsel_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT FK_counsel_party_side
        FOREIGN KEY (party_side) REFERENCES con.vocab_counsel_side (code)
);
GO

CREATE TABLE con.brief (
    brief_id      BIGINT IDENTITY(1,1) NOT NULL,
    docket_id     NVARCHAR(50)  NOT NULL,
    entry_id      INT           NULL,
    title         NVARCHAR(400) NULL,
    party_side    NVARCHAR(20)  NULL,
    attorney_name NVARCHAR(200) NULL,
    firm          NVARCHAR(200) NULL,
    filed_date    DATE          NULL,
    page_count    INT           NULL,
    CONSTRAINT PK_brief PRIMARY KEY (brief_id),
    CONSTRAINT FK_brief_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT FK_brief_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_brief_party_side
        FOREIGN KEY (party_side) REFERENCES con.vocab_counsel_side (code)
);
GO

CREATE TABLE con.proceeding_stage (
    stage_id         BIGINT IDENTITY(1,1) NOT NULL,
    docket_id        NVARCHAR(50)  NOT NULL,
    stage_num        NVARCHAR(10)  NULL,
    stage_label      NVARCHAR(80)  NULL,
    court            NVARCHAR(200) NULL,
    title            NVARCHAR(300) NULL,
    cite             NVARCHAR(200) NULL,
    stage_date       DATE          NULL,
    outcome          NVARCHAR(60)  NULL,
    summary          NVARCHAR(MAX) NULL,
    filings_count    INT           NULL,
    decision_maker   NVARCHAR(200) NULL,
    duration_days    INT           NULL,
    is_current       BIT           NOT NULL CONSTRAINT DF_proceeding_stage_is_current DEFAULT 0,
    has_opinion      BIT           NOT NULL CONSTRAINT DF_proceeding_stage_has_opinion DEFAULT 0,
    opinion_entry_id INT           NULL,
    sort_order       INT           NULL,
    CONSTRAINT PK_proceeding_stage PRIMARY KEY (stage_id),
    CONSTRAINT FK_proceeding_stage_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT FK_proceeding_stage_outcome
        FOREIGN KEY (outcome) REFERENCES con.vocab_outcome (code),
    CONSTRAINT FK_proceeding_stage_opinion
        FOREIGN KEY (opinion_entry_id) REFERENCES con.document (entry_id)
);
GO

CREATE TABLE con.docket_event (
    event_id    BIGINT IDENTITY(1,1) NOT NULL,
    docket_id   NVARCHAR(50)  NOT NULL,
    event_date  DATE          NULL,
    event_type  NVARCHAR(20)  NULL,
    court       NVARCHAR(200) NULL,
    description NVARCHAR(MAX) NULL,
    actor       NVARCHAR(200) NULL,
    entry_id    INT           NULL,
    CONSTRAINT PK_docket_event PRIMARY KEY (event_id),
    CONSTRAINT FK_docket_event_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id),
    CONSTRAINT FK_docket_event_event_type
        FOREIGN KEY (event_type) REFERENCES con.vocab_event_type (code),
    CONSTRAINT FK_docket_event_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id)
);
GO

-- ---------------------------------------------------------------------------
-- Statute cross-references (self-referencing pair; NO ACTION on both FKs).
-- ---------------------------------------------------------------------------

CREATE TABLE con.statute_xref (
    from_statute_id NVARCHAR(40) NOT NULL,
    to_statute_id   NVARCHAR(40) NOT NULL,
    CONSTRAINT PK_statute_xref PRIMARY KEY (from_statute_id, to_statute_id),
    CONSTRAINT FK_statute_xref_from
        FOREIGN KEY (from_statute_id) REFERENCES con.statute (statute_id),
    CONSTRAINT FK_statute_xref_to
        FOREIGN KEY (to_statute_id) REFERENCES con.statute (statute_id)
);
GO

-- ---------------------------------------------------------------------------
-- Workspace: wiki, research projects, alerts, deadline rules.
-- ---------------------------------------------------------------------------

CREATE TABLE con.wiki_article (
    article_id NVARCHAR(60)  NOT NULL,
    group_name NVARCHAR(120) NULL,
    title      NVARCHAR(300) NULL,
    toc_json   NVARCHAR(MAX) NULL,
    body_json  NVARCHAR(MAX) NULL,
    status     NVARCHAR(20)  NULL,
    updated_at DATETIME2     NULL,
    CONSTRAINT PK_wiki_article PRIMARY KEY (article_id),
    CONSTRAINT CK_wiki_article_toc_json CHECK (ISJSON(toc_json) = 1),
    CONSTRAINT CK_wiki_article_body_json CHECK (ISJSON(body_json) = 1)
);
GO

CREATE TABLE con.wiki_revision (
    revision_id  BIGINT IDENTITY(1,1) NOT NULL,
    article_id   NVARCHAR(60)  NOT NULL,
    author       NVARCHAR(200) NULL,
    submitted_at DATETIME2     NOT NULL CONSTRAINT DF_wiki_revision_submitted_at DEFAULT SYSUTCDATETIME(),
    status       NVARCHAR(20)  NULL,
    diff_json    NVARCHAR(MAX) NULL,
    CONSTRAINT PK_wiki_revision PRIMARY KEY (revision_id),
    CONSTRAINT FK_wiki_revision_article
        FOREIGN KEY (article_id) REFERENCES con.wiki_article (article_id),
    CONSTRAINT CK_wiki_revision_status
        CHECK (status IN (N'pending', N'approved', N'rejected')),
    CONSTRAINT CK_wiki_revision_diff_json CHECK (ISJSON(diff_json) = 1)
);
GO

CREATE TABLE con.research_project (
    project_id  NVARCHAR(60)  NOT NULL,
    owner_upn   NVARCHAR(200) NULL,
    name        NVARCHAR(300) NULL,
    description NVARCHAR(MAX) NULL,
    tags_json   NVARCHAR(MAX) NULL,
    status      NVARCHAR(20)  NOT NULL CONSTRAINT DF_research_project_status DEFAULT N'open',
    created_at  DATETIME2     NOT NULL CONSTRAINT DF_research_project_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_research_project PRIMARY KEY (project_id),
    CONSTRAINT CK_research_project_tags_json CHECK (ISJSON(tags_json) = 1)
);
GO

CREATE TABLE con.project_item (
    item_id    BIGINT IDENTITY(1,1) NOT NULL,
    project_id NVARCHAR(60)  NOT NULL,
    entry_id   INT           NULL,
    docket_id  NVARCHAR(50)  NULL,
    flagged    BIT           NOT NULL CONSTRAINT DF_project_item_flagged DEFAULT 0,
    note       NVARCHAR(MAX) NULL,
    CONSTRAINT PK_project_item PRIMARY KEY (item_id),
    CONSTRAINT FK_project_item_project
        FOREIGN KEY (project_id) REFERENCES con.research_project (project_id),
    CONSTRAINT FK_project_item_document
        FOREIGN KEY (entry_id) REFERENCES con.document (entry_id),
    CONSTRAINT FK_project_item_matter
        FOREIGN KEY (docket_id) REFERENCES con.matter (docket_id)
);
GO

CREATE TABLE con.saved_alert (
    alert_id   NVARCHAR(60)  NOT NULL,
    owner_upn  NVARCHAR(200) NULL,
    name       NVARCHAR(300) NULL,
    query_json NVARCHAR(MAX) NULL,
    scope      NVARCHAR(20)  NULL,
    frequency  NVARCHAR(20)  NULL,
    active     BIT           NOT NULL CONSTRAINT DF_saved_alert_active DEFAULT 1,
    created_at DATETIME2     NOT NULL CONSTRAINT DF_saved_alert_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_saved_alert PRIMARY KEY (alert_id),
    CONSTRAINT CK_saved_alert_query_json CHECK (ISJSON(query_json) = 1)
);
GO

-- deadline_rule structure lives here (0006); rows are seeded in 0009 to match
-- common/deadline_rules.py. FK to vocab_docket_family resolves because that
-- vocab table is created above in this same migration.
CREATE TABLE con.deadline_rule (
    rule_id       NVARCHAR(60)  NOT NULL,
    docket_family NVARCHAR(20)  NULL,
    trigger_event NVARCHAR(120) NULL,
    offset_days   INT           NULL,
    basis_statute NVARCHAR(40)  NULL,
    description   NVARCHAR(MAX) NULL,
    CONSTRAINT PK_deadline_rule PRIMARY KEY (rule_id),
    CONSTRAINT FK_deadline_rule_docket_family
        FOREIGN KEY (docket_family) REFERENCES con.vocab_docket_family (code),
    CONSTRAINT FK_deadline_rule_basis_statute
        FOREIGN KEY (basis_statute) REFERENCES con.statute (statute_id)
);
GO

-- ---------------------------------------------------------------------------
-- Indexes (DESIGN.md "Indexes (0006)").
-- ---------------------------------------------------------------------------

CREATE NONCLUSTERED INDEX IX_citation_citing_entry_id  ON con.citation (citing_entry_id);
CREATE NONCLUSTERED INDEX IX_citation_cited_entry_id    ON con.citation (cited_entry_id);
CREATE NONCLUSTERED INDEX IX_citation_cited_statute_id  ON con.citation (cited_statute_id);
GO

CREATE NONCLUSTERED INDEX IX_document_topic_topic_id ON con.document_topic (topic_id);
GO

CREATE NONCLUSTERED INDEX IX_opinion_decided_date ON con.opinion (decided_date);
GO

CREATE NONCLUSTERED INDEX IX_proceeding_stage_docket_id ON con.proceeding_stage (docket_id);
GO

CREATE NONCLUSTERED INDEX IX_docket_event_docket_id ON con.docket_event (docket_id);
CREATE NONCLUSTERED INDEX IX_docket_event_event_date ON con.docket_event (event_date);
GO

CREATE NONCLUSTERED INDEX IX_counsel_entry_id ON con.counsel (entry_id);
CREATE NONCLUSTERED INDEX IX_counsel_docket_id ON con.counsel (docket_id);
GO

CREATE NONCLUSTERED INDEX IX_brief_docket_id ON con.brief (docket_id);
GO

CREATE NONCLUSTERED INDEX IX_reporter_citation_entry_id ON con.reporter_citation (entry_id);
GO

CREATE NONCLUSTERED INDEX IX_headnote_entry_id ON con.headnote (entry_id);
GO
