# Report layout — recommended pages

Three pages plus a hidden drill-through page. Field references use the
`queries.pq` table names and `measures.dax` measure names.

Model prep that affects visuals:

- Select `Matters[county]` > Column tools > **Data category = County** so the map
  geocodes correctly; consider a page-level filter `Country/Region = Georgia (US)`
  or append ", Georgia" via a calculated column if Bing geocoding is ambiguous.
- Sort `Dates[MonthName]` by `Dates[MonthNum]` (Column tools > Sort by column).
- Format `Approval Rate %`, `Documents Validated %`, `Matters Flagged %` as
  percentages.

## Page 1 — Overview (trends)

| Visual | Fields / measures | Notes |
|---|---|---|
| KPI cards (row of 5) | `Total Matters`, `Total Documents`, `Approval Rate %`, `Median Days LOI to Decision`, `Documents Validated %` | The at-a-glance health row. Put `LOI to Decision Sample Size` in the median card's tooltip. |
| Clustered column chart | X: `Matters[year_filed]` · Y: `Total Matters` · Legend: `Matters[matter_type]` | Filing volume by year and matter type. |
| Line chart | X: `Dates[YearMonth]` (or Date hierarchy) · Y: `Changes Detected`, `Revalidations Flagged` | Repository churn from `con.change_log`; uses the `ChangeLog[detected_date]` → `Dates` relationship. |
| Stacked column chart | X: `Dates[YearQuarter]` · Y: count of `WeeklyEvents[event_id]` · Legend: `WeeklyEvents[section]` | Weekly-report pipeline flow (LOIs, new applications, approvals, denials...). Uses `WeeklyEvents[report_date]` → `Dates`. |
| Slicers | `Matters[year_filed]`, `Matters[matter_type]`, `MatterServiceTypes[service_type]` | Sync these slicers to all pages (View > Sync slicers). |

## Page 2 — Outcomes by service type & county

| Visual | Fields / measures | Notes |
|---|---|---|
| Filled map (or shape map) | Location: `Matters[county]` · Color saturation: `Approval Rate %` · Tooltips: `Total Matters`, `Matters Approved`, `Decided Matters` | The county picture. Filled map needs Data category = County (see above). If Bing geocoding misplaces counties, switch to a Shape map with a Georgia counties TopoJSON. |
| Matrix | Rows: `MatterServiceTypes[service_type]` · Values: `Matters (by Service Type)`, `Approval Rate % (by Service Type)`, `Median Days LOI to Decision` | Sort by matter count descending. Remember multi-service matters count once per service type. |
| 100% stacked bar chart | Y: `Matters[final_outcome]` · X: `Total Matters` · Legend: `Matters[matter_type]` | Distribution across the 13 outcome codes; filter out blanks with a visual-level filter if noise. |
| Clustered bar chart | Y: `Matters[action_type]` · X: `Total Matters`, `Matters Approved` | Which action types get approved. |
| Slicers | `Matters[county]`, `Matters[final_outcome]`, `Matters[year_filed]` | |

## Page 3 — Completeness audit

| Visual | Fields / measures | Notes |
|---|---|---|
| KPI cards (row) | `Documents Validated %`, `Unvalidated Documents`, `Rejected Documents`, `Corrected Documents`, `Matters Missing Final Outcome`, `Matters Missing County`, `Matters With Completeness Flags`, `Stub Matters` | The full audit set from `measures.dax`. |
| Donut chart | Legend: `Documents[validation_status]` · Values: `Total Documents` | Exactly four slices (Unvalidated/Validated/Corrected/Rejected). |
| Table | `Matters[docket_id]`, `Matters[applicant]`, `Matters[county]`, `Matters[year_filed]`, `Matters[final_outcome]`, `Matters[completeness_flags]` · Visual filter: `Matters[has_completeness_flags]` = 1 | The work queue: every flagged matter with its raw JSON flags visible. |
| Table | `Documents[entry_id]`, `Documents[docket_id]`, `Documents[file_name]`, `Documents[doc_type]`, `Documents[validation_status]`, `Documents[docview_url]` · Visual filter: `validation_status` is `Unvalidated` or `Rejected` | Set `docview_url`'s Data category = **Web URL** (Column tools) so analysts click straight into DocView. |
| Stacked bar | Y: `Documents[doc_type]` · X: `Total Documents` · Legend: `Documents[validation_status]` | Which document types lag on validation. |

## Hidden page — Matter drill-through

Add a drill-through page keyed on `Matters[docket_id]` so right-click > Drill
through works from any visual:

- Multi-row card: `applicant`, `facility`, `matter_type`, `action_type`,
  `county`, `service_area`, `bed_count`, `year_filed`, `final_outcome`,
  `final_decision_date`, `Matters[service_types]` (the aggregated string).
- Table of the matter's documents (fields as in Page 3's document table,
  including the clickable `docview_url`).
- Table of the matter's weekly events: `report_date`, `section`,
  `project_description`, `cost`, `decision_deadline`, `decision_date`.
