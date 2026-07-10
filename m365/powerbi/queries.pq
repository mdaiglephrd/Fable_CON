// ============================================================================
// Power Query M source queries for the CON database (Azure SQL).
//
// How to use (Power BI Desktop):
//   1. Home > Manage Parameters > New Parameter:
//        Name: SqlServer    Type: Text   Current Value: <your server>.database.windows.net
//        Name: SqlDatabase  Type: Text   Current Value: <your database, e.g. condb>
//   2. For EACH block below: Home > New Source > Blank Query, open the
//      Advanced Editor, paste everything between the BEGIN/END markers of that
//      block (the whole let..in expression), then rename the query to the name
//      shown in the marker.
//   3. The Matters query uses Value.NativeQuery (documented SQL text). Approve
//      the "native database query" prompt — it is a read-only SELECT.
//
// All table/column names match schema `con` in DESIGN.md exactly.
// ============================================================================


// ---------------------------------------------------------------------------
// BEGIN QUERY: Matters
// One row per matter. Service types are aggregated to a single '; '-separated
// string with STRING_AGG (native SQL is the cleanest way to do this; the pure-M
// alternative is Table.NestedJoin + Text.Combine, which downloads the child
// table and merges client-side). Also derives two audit flags from
// completeness_flags (a JSON array column):
//   has_completeness_flags = 1 when the array is non-empty
//   is_stub                = 1 when it contains 'stub_from_weekly_report'
// ---------------------------------------------------------------------------
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    MattersSql = "
SELECT
    m.docket_id,
    m.applicant,
    m.facility,
    m.matter_type,
    m.action_type,
    m.county,
    m.service_area,
    m.bed_count,
    m.year_filed,
    m.final_outcome,
    m.final_decision_date,
    m.highest_review_level,
    m.completeness_flags,
    m.created_at,
    m.updated_at,
    st.service_types,
    CASE
        WHEN m.completeness_flags IS NOT NULL
         AND EXISTS (SELECT 1 FROM OPENJSON(m.completeness_flags))
        THEN 1 ELSE 0
    END AS has_completeness_flags,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM OPENJSON(m.completeness_flags) f
            WHERE f.value = 'stub_from_weekly_report'
        )
        THEN 1 ELSE 0
    END AS is_stub
FROM con.matter AS m
OUTER APPLY (
    SELECT STRING_AGG(mst.service_type, '; ')
               WITHIN GROUP (ORDER BY mst.service_type) AS service_types
    FROM con.matter_service_type AS mst
    WHERE mst.docket_id = m.docket_id
) AS st;
",
    Matters = Value.NativeQuery(Source, MattersSql, null, [EnableFolding = false]),
    Typed = Table.TransformColumnTypes(
        Matters,
        {
            {"docket_id", type text},
            {"applicant", type text},
            {"facility", type text},
            {"matter_type", type text},
            {"action_type", type text},
            {"county", type text},
            {"service_area", type text},
            {"bed_count", Int64.Type},
            {"year_filed", Int64.Type},
            {"final_outcome", type text},
            {"final_decision_date", type date},
            {"highest_review_level", Int64.Type},
            {"completeness_flags", type text},
            {"created_at", type datetime},
            {"updated_at", type datetime},
            {"service_types", type text},
            {"has_completeness_flags", Int64.Type},
            {"is_stub", Int64.Type}
        }
    )
in
    Typed
// END QUERY: Matters


// ---------------------------------------------------------------------------
// BEGIN QUERY: MatterServiceTypes
// The con.matter_service_type bridge table, one row per (docket_id, service_type).
// Needed to SLICE by individual service type (the aggregated string on Matters
// is for display only). Relate MatterServiceTypes[docket_id] -> Matters[docket_id].
// ---------------------------------------------------------------------------
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    ServiceTypes = Source{[Schema = "con", Item = "matter_service_type"]}[Data],
    Kept = Table.SelectColumns(ServiceTypes, {"docket_id", "service_type"})
in
    Kept
// END QUERY: MatterServiceTypes


// ---------------------------------------------------------------------------
// BEGIN QUERY: Documents
// con.document, one row per Laserfiche entry. Adds doc_year for quick grouping.
// parties (JSON array) and source_path are kept for tooltips/detail tables.
// ---------------------------------------------------------------------------
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    Documents = Source{[Schema = "con", Item = "document"]}[Data],
    Kept = Table.SelectColumns(
        Documents,
        {
            "entry_id", "docket_id", "docview_url", "file_name", "doc_type",
            "decision_level", "phase", "page_count", "doc_date",
            "decision_maker", "outcome", "parties", "source_path",
            "ocr_status", "ocr_confidence", "validation_status",
            "validated_by", "validated_date", "duplicate_of", "updated_at"
        }
    ),
    AddDocYear = Table.AddColumn(
        Kept, "doc_year",
        each if [doc_date] = null then null else Date.Year([doc_date]),
        Int64.Type
    )
in
    AddDocYear
// END QUERY: Documents


// ---------------------------------------------------------------------------
// BEGIN QUERY: WeeklyEvents
// con.weekly_report_event. raw_text and dedupe_hash are excluded (large, not
// needed for reporting). Rows with docket_id = null will not relate to Matters.
// ---------------------------------------------------------------------------
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    Events = Source{[Schema = "con", Item = "weekly_report_event"]}[Data],
    Kept = Table.SelectColumns(
        Events,
        {
            "event_id", "report_date", "report_file", "section", "docket_id",
            "docket_raw", "applicant", "project_description", "county", "cost",
            "opposition", "filing_date", "decision_deadline", "decision_date"
        }
    )
in
    Kept
// END QUERY: WeeklyEvents


// ---------------------------------------------------------------------------
// BEGIN QUERY: ChangeLog
// con.change_log. details (JSON) kept for drill-through inspection; a derived
// detected_date (date-typed) supports the relationship to the Dates table.
// ---------------------------------------------------------------------------
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    Changes = Source{[Schema = "con", Item = "change_log"]}[Data],
    Kept = Table.SelectColumns(
        Changes,
        {
            "change_id", "entry_id", "change_type", "old_snapshot_id",
            "new_snapshot_id", "details", "in_scope", "revalidation_flagged",
            "detected_at"
        }
    ),
    AddDetectedDate = Table.AddColumn(
        Kept, "detected_date",
        each Date.From([detected_at]),
        type date
    )
in
    AddDetectedDate
// END QUERY: ChangeLog


// ---------------------------------------------------------------------------
// BEGIN QUERY: Dates
// Pure-M date dimension. No database access. Covers 1990-01-01 through the end
// of the current year (CON records reach well back; adjust StartDate if your
// earliest doc_date/report_date is older). Mark this table as the model's date
// table (Table tools > Mark as date table > Date).
// ---------------------------------------------------------------------------
let
    StartDate = #date(1990, 1, 1),
    EndDate = #date(Date.Year(Date.From(DateTime.LocalNow())), 12, 31),
    DayCount = Duration.Days(EndDate - StartDate) + 1,
    DateList = List.Dates(StartDate, DayCount, #duration(1, 0, 0, 0)),
    AsTable = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}),
    TypedDate = Table.TransformColumnTypes(AsTable, {{"Date", type date}}),
    AddYear = Table.AddColumn(TypedDate, "Year", each Date.Year([Date]), Int64.Type),
    AddMonthNum = Table.AddColumn(AddYear, "MonthNum", each Date.Month([Date]), Int64.Type),
    AddMonthName = Table.AddColumn(AddMonthNum, "MonthName", each Date.ToText([Date], "MMM"), type text),
    AddQuarter = Table.AddColumn(
        AddMonthName, "Quarter",
        each "Q" & Number.ToText(Date.QuarterOfYear([Date])),
        type text
    ),
    AddYearMonth = Table.AddColumn(AddQuarter, "YearMonth", each Date.ToText([Date], "yyyy-MM"), type text),
    AddYearQuarter = Table.AddColumn(
        AddYearMonth, "YearQuarter",
        each Number.ToText(Date.Year([Date])) & " Q" & Number.ToText(Date.QuarterOfYear([Date])),
        type text
    )
in
    AddYearQuarter
// END QUERY: Dates
