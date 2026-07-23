-- 0013_app_user.sql
-- App-level user profile, upserted by GET /me (api/routers/users.py) from the
-- platform-authenticated caller. SWA/App Service Easy Auth forwards identity
-- via the x-ms-client-principal header (api/auth.py parses it); user_id is
-- the stable Entra object id (oid claim) when present, else the SWA userId --
-- either way a stable key across UPN/email changes, unlike owner_upn on
-- con.research_project / con.saved_alert which is a display value.
--
-- upn/email are optional (not every principal carries both) and not
-- guaranteed unique across every tenant configuration, so uniqueness on upn
-- is a filtered index (skips NULLs) rather than a table-level UNIQUE column.

CREATE TABLE con.app_user (
    user_id           NVARCHAR(128) NOT NULL,
    upn               NVARCHAR(256) NULL,
    email             NVARCHAR(256) NULL,
    display_name      NVARCHAR(256) NULL,
    identity_provider NVARCHAR(64)  NULL,
    created_at        DATETIME2     NOT NULL CONSTRAINT DF_app_user_created_at DEFAULT SYSUTCDATETIME(),
    last_seen_at      DATETIME2     NOT NULL CONSTRAINT DF_app_user_last_seen_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_app_user PRIMARY KEY (user_id)
);
GO

CREATE UNIQUE INDEX UQ_app_user_upn ON con.app_user (upn) WHERE upn IS NOT NULL;
GO
