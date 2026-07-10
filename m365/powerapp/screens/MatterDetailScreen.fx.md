# MatterDetailScreen

**Purpose**: everything about one matter (`varSelectedMatter`, set by
BrowseScreen): the matter's fields, its service types, its documents from
`con.document` (each row launches the Laserfiche DocView URL), and its weekly
report events from `con.weekly_report_event`.

## Control tree

```
MatterDetailScreen
├─ btnBack               (Button)          "< Back"
├─ lblDocket             (Label)           big docket_id header
├─ lblMatterFields       (Label)           multi-line matter summary
├─ lblServiceTypes       (Label)           service types (from child table)
├─ lblFlags              (Label)           completeness_flags JSON, if any
├─ lblDocsHeader         (Label)           "Documents"
├─ galDocuments          (Vertical gallery)
│   ├─ lblDocTitle       (Title label)
│   ├─ lblDocMeta        (Subtitle label)
│   ├─ lblDocValidation  (Body label)      validation status badge
│   └─ icoOpenDoc        (Icon: OpenInNewWindow)  launches docview_url
├─ lblEventsHeader       (Label)           "Weekly report events"
└─ galEvents             (Vertical gallery)
    ├─ lblEvtTitle       (Title label)
    └─ lblEvtMeta        (Subtitle label)
```

## btnBack (Button)

```powerfx
// Text
"< Back"
```

```powerfx
// OnSelect
Back()
```

## lblDocket (Label)

```powerfx
// Text
varSelectedMatter.docket_id
```

## lblMatterFields (Label)

Set `AutoHeight` to `true` and font size ~12.

```powerfx
// Text — Char(10) is a newline
"Applicant: " & Coalesce(varSelectedMatter.applicant, "—") & Char(10) &
"Facility: " & Coalesce(varSelectedMatter.facility, "—") & Char(10) &
"Matter type: " & Coalesce(varSelectedMatter.matter_type, "—") &
    "   Action: " & Coalesce(varSelectedMatter.action_type, "—") & Char(10) &
"County: " & Coalesce(varSelectedMatter.county, "—") &
    "   Service area: " & Coalesce(varSelectedMatter.service_area, "—") & Char(10) &
"Beds: " & If(IsBlank(varSelectedMatter.bed_count), "—", Text(varSelectedMatter.bed_count)) &
    "   Year filed: " & If(IsBlank(varSelectedMatter.year_filed), "—", Text(varSelectedMatter.year_filed)) & Char(10) &
"Final outcome: " & Coalesce(varSelectedMatter.final_outcome, "— (not recorded)") &
    "   Decision date: " &
    If(
        IsBlank(varSelectedMatter.final_decision_date),
        "—",
        Text(varSelectedMatter.final_decision_date, DateTimeFormat.ShortDate)
    )
```

## lblServiceTypes (Label)

```powerfx
// Text — reads the child table con.matter_service_type for this docket.
// Filter(child, docket_id = <constant>) is delegable; Concat runs on the
// (small) result set locally.
"Service types: " &
Coalesce(
    Concat(
        Filter('con.matter_service_type', docket_id = varSelectedMatter.docket_id),
        service_type,
        "; "
    ),
    "—"
)
```

## lblFlags (Label)

```powerfx
// Text — raw completeness_flags JSON array; hidden when empty.
"Completeness flags: " & varSelectedMatter.completeness_flags
```

```powerfx
// Visible
!IsBlank(varSelectedMatter.completeness_flags)
    && varSelectedMatter.completeness_flags <> "[]"
```

## galDocuments (Vertical gallery)

```powerfx
// Items — delegable: equality filter + SortByColumns on a date column.
SortByColumns(
    Filter('con.document', docket_id = varSelectedMatter.docket_id),
    "doc_date", SortOrder.Descending
)
```

### lblDocTitle (Title label inside gallery)

```powerfx
// Text
Coalesce(ThisItem.doc_type, "Other") & " — " & Coalesce(ThisItem.file_name, "(no file name)")
```

### lblDocMeta (Subtitle label inside gallery)

```powerfx
// Text
"Entry " & Text(ThisItem.entry_id) &
If(IsBlank(ThisItem.doc_date), "", " · " & Text(ThisItem.doc_date, DateTimeFormat.ShortDate)) &
If(IsBlank(ThisItem.phase), "", " · " & ThisItem.phase) &
If(IsBlank(ThisItem.outcome), "", " · " & ThisItem.outcome) &
If(IsBlank(ThisItem.page_count), "", " · " & Text(ThisItem.page_count) & " pp")
```

### lblDocValidation (Body label inside gallery)

```powerfx
// Text
ThisItem.validation_status &
If(
    ThisItem.validation_status = "Validated" || ThisItem.validation_status = "Corrected",
    " by " & Coalesce(ThisItem.validated_by, "?"),
    ""
)
```

```powerfx
// Color — green for reviewed, amber for unvalidated, red for rejected
Switch(
    ThisItem.validation_status,
    "Validated", Color.Green,
    "Corrected", Color.DarkGreen,
    "Rejected", Color.Red,
    Color.DarkOrange
)
```

### icoOpenDoc (Icon, set Icon property to `Icon.OpenInNewWindow`)

```powerfx
// OnSelect — open the Laserfiche DocView link for this document
Launch(ThisItem.docview_url)
```

```powerfx
// Visible — some rows may lack a URL
!IsBlank(ThisItem.docview_url)
```

```powerfx
// Tooltip
"Open in DocView"
```

## galEvents (Vertical gallery)

```powerfx
// Items — weekly report events for this docket, newest report first.
// Equality filter on docket_id is delegable.
SortByColumns(
    Filter('con.weekly_report_event', docket_id = varSelectedMatter.docket_id),
    "report_date", SortOrder.Descending
)
```

### lblEvtTitle (Title label inside gallery)

```powerfx
// Text — section code + report date
ThisItem.section & " · " & Text(ThisItem.report_date, DateTimeFormat.ShortDate)
```

### lblEvtMeta (Subtitle label inside gallery)

```powerfx
// Text
Coalesce(ThisItem.project_description, "(no description)") &
If(IsBlank(ThisItem.cost), "", " · $" & Text(ThisItem.cost, "#,##0")) &
If(
    IsBlank(ThisItem.decision_date),
    If(
        IsBlank(ThisItem.decision_deadline),
        "",
        " · deadline " & Text(ThisItem.decision_deadline, DateTimeFormat.ShortDate)
    ),
    " · decided " & Text(ThisItem.decision_date, DateTimeFormat.ShortDate)
)
```

---

## Notes

- Both child galleries filter on `docket_id = <constant>` — fully delegable, so
  they are correct regardless of table size.
- `varSelectedMatter` is a record variable set on BrowseScreen. If you want the
  screen to survive app restarts / deep links, replace it with a
  `LookUp('con.matter', docket_id = Param("docket"))` in `OnVisible`.
- The gallery shows `duplicate_of` implicitly via file name; if duplicate
  tracking matters in the UI, add a body label:
  `If(IsBlank(ThisItem.duplicate_of), "", "Duplicate of entry " & Text(ThisItem.duplicate_of))`.
