# BrowseScreen

**Purpose**: find matters fast. A search box (applicant / facility / docket), five
filters (county, matter type, final outcome, year filed, service type), and a
gallery of matching `con.matter` rows. Selecting a row opens MatterDetailScreen.

Vocabulary dropdowns are fed from the vocab tables themselves
(`con.county`, `con.vocab_matter_type`, `con.vocab_outcome`,
`con.vocab_service_type`) so the app can never drift from the controlled values.

## Control tree

```
BrowseScreen
├─ lblTitle            (Label)          "GA CON Matters"
├─ txtSearch           (Text input)     search box
├─ cmbCounty           (Combo box)      county filter
├─ cmbMatterType       (Combo box)      matter type filter
├─ cmbOutcome          (Combo box)      final outcome filter
├─ cmbYear             (Combo box)      year filed filter
├─ cmbServiceType      (Combo box)      service type filter
├─ btnClearFilters     (Button)         reset everything
├─ lblResultCount      (Label)          "N matters shown"
├─ galMatters          (Vertical gallery, layout: Title, subtitle, and body)
│   ├─ lblGalDocket    (Title label)
│   ├─ lblGalApplicant (Subtitle label)
│   └─ lblGalMeta      (Body label)
└─ btnGoValidation     (Button)         jump to ValidationScreen
```

Combo boxes (not classic dropdowns) are used deliberately: a combo box can have
**nothing selected**, which is our "no filter" state, and it gives type-ahead over
159 counties for free. Set each combo box `SelectMultiple` to `false`.

## Screen

```powerfx
// BrowseScreen.OnVisible — nothing to initialize; filters keep their state.
false
```

## txtSearch (Text input)

```powerfx
// HintText
"Search applicant, facility, or docket..."
```

```powerfx
// Default
""
```

## cmbCounty (Combo box)

```powerfx
// Items — the 159 counties from the vocab table (column: name)
Sort('con.county', name, SortOrder.Ascending)
```

```powerfx
// Fields: set the primary text to "name" via the Fields pane, or:
// DisplayFields
["name"]
```

```powerfx
// SearchFields
["name"]
```

```powerfx
// SelectMultiple
false
```

```powerfx
// InputTextPlaceholder
"County"
```

## cmbMatterType (Combo box)

```powerfx
// Items — con.vocab_matter_type (column: code)
'con.vocab_matter_type'
```

```powerfx
// DisplayFields
["code"]
```

```powerfx
// SearchFields
["code"]
```

```powerfx
// SelectMultiple
false
```

```powerfx
// InputTextPlaceholder
"Matter type"
```

## cmbOutcome (Combo box)

```powerfx
// Items — con.vocab_outcome (column: code); used against matter.final_outcome
'con.vocab_outcome'
```

```powerfx
// DisplayFields
["code"]
```

```powerfx
// SearchFields
["code"]
```

```powerfx
// SelectMultiple
false
```

```powerfx
// InputTextPlaceholder
"Final outcome"
```

## cmbYear (Combo box)

```powerfx
// Items — static year list (delegation-safe: Distinct() over year_filed would
// be a non-delegable scan of con.matter). 1990..current year, newest first.
Sort(
    ForAll(Sequence(Year(Today()) - 1989, 1990), {year: Value}),
    year,
    SortOrder.Descending
)
```

```powerfx
// DisplayFields
["year"]
```

```powerfx
// SelectMultiple
false
```

```powerfx
// InputTextPlaceholder
"Year filed"
```

## cmbServiceType (Combo box)

```powerfx
// Items — con.vocab_service_type (column: code)
'con.vocab_service_type'
```

```powerfx
// DisplayFields
["code"]
```

```powerfx
// SearchFields
["code"]
```

```powerfx
// SelectMultiple
false
```

```powerfx
// InputTextPlaceholder
"Service type"
```

## btnClearFilters (Button)

```powerfx
// Text
"Clear"
```

```powerfx
// OnSelect
Reset(txtSearch);
Reset(cmbCounty);
Reset(cmbMatterType);
Reset(cmbOutcome);
Reset(cmbYear);
Reset(cmbServiceType)
```

## galMatters (Vertical gallery)

```powerfx
// Items
// Layered so the hot path stays delegable to SQL:
//   * Search() over text columns    — DELEGABLE for SQL Server (text)
//   * Filter() with =, IsBlank(control-value) constants — DELEGABLE
//   * the service-type membership test (`in` against a one-column table)
//     — NOT delegable to SQL; see the delegation notes below.
// SortByColumns — delegable.
SortByColumns(
    Search(
        Filter(
            'con.matter',
            (IsBlank(cmbCounty.Selected.name) || county = cmbCounty.Selected.name),
            (IsBlank(cmbMatterType.Selected.code) || matter_type = cmbMatterType.Selected.code),
            (IsBlank(cmbOutcome.Selected.code) || final_outcome = cmbOutcome.Selected.code),
            (IsBlank(cmbYear.Selected.year) || year_filed = cmbYear.Selected.year),
            (
                IsBlank(cmbServiceType.Selected.code)
                || docket_id in ShowColumns(
                        Filter(
                            'con.matter_service_type',
                            service_type = cmbServiceType.Selected.code
                        ),
                        "docket_id"
                   ).docket_id
            )
        ),
        txtSearch.Text,
        "applicant", "facility", "docket_id"
    ),
    "year_filed", SortOrder.Descending,
    "docket_id", SortOrder.Ascending
)
```

```powerfx
// OnSelect — remember the matter and open the detail screen
Set(varSelectedMatter, ThisItem);
Navigate(MatterDetailScreen, ScreenTransition.Cover)
```

### lblGalDocket (Title label inside gallery)

```powerfx
// Text
ThisItem.docket_id & If(IsBlank(ThisItem.final_outcome), "", " — " & ThisItem.final_outcome)
```

### lblGalApplicant (Subtitle label inside gallery)

```powerfx
// Text
Coalesce(ThisItem.applicant, "(applicant unknown)")
    & If(IsBlank(ThisItem.facility), "", " · " & ThisItem.facility)
```

### lblGalMeta (Body label inside gallery)

```powerfx
// Text
Coalesce(ThisItem.matter_type, "?")
    & " · " & Coalesce(ThisItem.county, "no county")
    & " · " & If(IsBlank(ThisItem.year_filed), "no year", Text(ThisItem.year_filed))
```

## lblResultCount (Label)

```powerfx
// Text — CountRows on a filtered SQL source may itself hit delegation limits;
// this intentionally reports only what the gallery has loaded so far.
Text(CountRows(galMatters.AllItems)) & " matters shown (scroll loads more)"
```

## btnGoValidation (Button)

```powerfx
// Text
"Validation queue"
```

```powerfx
// OnSelect
Navigate(ValidationScreen, ScreenTransition.Cover)
```

---

## Delegation warnings & mitigations (SQL Server)

Reference: [functions delegable to SQL Server](https://learn.microsoft.com/power-apps/maker/canvas-apps/connections/sql-connection-overview#power-apps-functions-and-operations-delegable-to-sql-server).

What delegates in the Items formula above:

- `Search(..., "applicant", "facility", "docket_id")` — **delegable**: SQL Server
  supports `Search` on text columns (it becomes `LIKE '%…%'` server-side).
- `Filter` predicates of the form `column = <constant>` — **delegable**; the
  `IsBlank(cmbX.Selected.…)` halves of each `||` are control values, i.e.
  constants at query time, so they don't break delegation. (Never call
  `IsBlank(column)` on a *SQL column* — that is not delegable; use
  `column <> Blank()` instead.)
- `SortByColumns` on number/text — **delegable**.

The one intentional exception:

- The **service-type** membership test (`docket_id in <one-column table>`) is
  **not delegable** to SQL Server; Power Apps evaluates it after pulling at most
  the Data-row-limit (500–2000) rows of the *outer* query. Consequences and
  mitigations:
  1. With no other filters and >2000 matching matters, a service-type-only filter
     can miss rows. In practice, pair it with county/year/search to keep the
     candidate set under the limit — the UI's whole point.
  2. Robust fix if service-type-first browsing matters to you: create a flattened
     SQL view and add it as a second data source, then point the gallery at it
     when a service type is chosen (one row per matter × service type, so a
     matter with 2 service types appears twice — acceptable in a filtered list):

     ```sql
     CREATE VIEW con.matter_service_browse AS
     SELECT m.docket_id, m.applicant, m.facility, m.matter_type, m.county,
            m.year_filed, m.final_outcome, mst.service_type
     FROM con.matter AS m
     JOIN con.matter_service_type AS mst ON mst.docket_id = m.docket_id;
     ```

     Then `Filter('con.matter_service_browse', service_type = cmbServiceType.Selected.code, ...)`
     is fully delegable. (Views are read-only in the SQL connector unless keyed —
     fine here, browsing never writes.)
  3. `CountRows` against SQL is not reliably delegable — hence `lblResultCount`
     counts only loaded rows and says so.
