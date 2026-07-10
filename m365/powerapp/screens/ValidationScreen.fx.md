# ValidationScreen

**Purpose**: the review queue. Shows documents with
`validation_status = 'Unvalidated'`; the reviewer opens the DocView link,
compares metadata against the source, then presses **Validate**, **Corrected**,
or **Reject**. Each button `Patch()`es `con.document` with the new
`validation_status`, `validated_by = User().Email`, and `validated_date` (UTC).

Allowed statuses (CHECK constraint on the column):
`'Unvalidated' | 'Validated' | 'Corrected' | 'Rejected'`.

## Control tree

```
ValidationScreen
├─ btnBackV             (Button)           "< Back"
├─ lblQueueTitle        (Label)            "Validation queue"
├─ lblQueueCount        (Label)            queue size (loaded rows)
├─ galQueue             (Vertical gallery)
│   ├─ lblQDocTitle     (Title label)
│   ├─ lblQDocMeta      (Subtitle label)
│   └─ icoQOpenDoc      (Icon: OpenInNewWindow)
└─ conReview            (Container / right pane, driven by galQueue.Selected)
    ├─ lblSelDoc        (Label)            selected doc summary
    ├─ btnOpenDocView   (Button)           "Open DocView"
    ├─ btnValidate      (Button)           mark Validated
    ├─ btnCorrected     (Button)           mark Corrected
    ├─ btnReject        (Button)           mark Rejected
    └─ lblPatchStatus   (Label)            last action feedback
```

## btnBackV (Button)

```powerfx
// Text
"< Back"
```

```powerfx
// OnSelect
Back()
```

## galQueue (Vertical gallery)

```powerfx
// Items — the queue. Equality on validation_status is delegable; oldest
// repo-created docs first so the backlog drains in order.
SortByColumns(
    Filter('con.document', validation_status = "Unvalidated"),
    "repo_date_created", SortOrder.Ascending
)
```

### lblQDocTitle (Title label inside gallery)

```powerfx
// Text
Coalesce(ThisItem.docket_id, "(no docket)") & " · " & Coalesce(ThisItem.file_name, "(no file name)")
```

### lblQDocMeta (Subtitle label inside gallery)

```powerfx
// Text
"Entry " & Text(ThisItem.entry_id) &
" · " & Coalesce(ThisItem.doc_type, "?") &
If(IsBlank(ThisItem.ocr_status), "", " · OCR " & ThisItem.ocr_status) &
If(IsBlank(ThisItem.ocr_confidence), "", " (" & Text(ThisItem.ocr_confidence) & ")")
```

### icoQOpenDoc (Icon, `Icon.OpenInNewWindow`)

```powerfx
// OnSelect
Launch(ThisItem.docview_url)
```

```powerfx
// Visible
!IsBlank(ThisItem.docview_url)
```

## lblQueueCount (Label)

```powerfx
// Text
Text(CountRows(galQueue.AllItems)) & " unvalidated documents loaded"
```

## conReview — right pane controls

All of these reference `galQueue.Selected` (the highlighted queue row).

### lblSelDoc (Label, AutoHeight = true)

```powerfx
// Text
If(
    IsBlank(galQueue.Selected),
    "Select a document from the queue.",
    "Entry " & Text(galQueue.Selected.entry_id) & Char(10) &
    "Docket: " & Coalesce(galQueue.Selected.docket_id, "—") & Char(10) &
    "File: " & Coalesce(galQueue.Selected.file_name, "—") & Char(10) &
    "Type: " & Coalesce(galQueue.Selected.doc_type, "—") &
        "   Phase: " & Coalesce(galQueue.Selected.phase, "—") & Char(10) &
    "Doc date: " &
        If(
            IsBlank(galQueue.Selected.doc_date),
            "—",
            Text(galQueue.Selected.doc_date, DateTimeFormat.ShortDate)
        ) & Char(10) &
    "Outcome: " & Coalesce(galQueue.Selected.outcome, "—") & Char(10) &
    "Source path: " & Coalesce(galQueue.Selected.source_path, "—")
)
```

### btnOpenDocView (Button)

```powerfx
// Text
"Open DocView"
```

```powerfx
// OnSelect
Launch(galQueue.Selected.docview_url)
```

```powerfx
// DisplayMode
If(
    IsBlank(galQueue.Selected) || IsBlank(galQueue.Selected.docview_url),
    DisplayMode.Disabled,
    DisplayMode.Edit
)
```

### btnValidate (Button)

```powerfx
// Text
"✓ Validate"
```

```powerfx
// OnSelect
// Exact Patch: keys on con.document's primary key (entry_id) via the record.
// validated_date: the DB convention is UTC (SYSUTCDATETIME() defaults), and
// Power Fx Now() is LOCAL time — DateAdd(Now(), TimeZoneOffset(), ...) converts
// local to UTC.
Patch(
    'con.document',
    galQueue.Selected,
    {
        validation_status: "Validated",
        validated_by: User().Email,
        validated_date: DateAdd(Now(), TimeZoneOffset(), TimeUnit.Minutes)
    }
);
If(
    IsEmpty(Errors('con.document')),
    UpdateContext({locLastAction: "Entry " & Text(galQueue.Selected.entry_id) & " marked Validated"}),
    UpdateContext({locLastAction: "FAILED: " & First(Errors('con.document')).Message})
)
```

```powerfx
// DisplayMode
If(IsBlank(galQueue.Selected), DisplayMode.Disabled, DisplayMode.Edit)
```

### btnCorrected (Button)

Use this after fixing metadata at the source (tag reload) or when recording that
the row was corrected during review.

```powerfx
// Text
"✎ Corrected"
```

```powerfx
// OnSelect
Patch(
    'con.document',
    galQueue.Selected,
    {
        validation_status: "Corrected",
        validated_by: User().Email,
        validated_date: DateAdd(Now(), TimeZoneOffset(), TimeUnit.Minutes)
    }
);
If(
    IsEmpty(Errors('con.document')),
    UpdateContext({locLastAction: "Entry " & Text(galQueue.Selected.entry_id) & " marked Corrected"}),
    UpdateContext({locLastAction: "FAILED: " & First(Errors('con.document')).Message})
)
```

```powerfx
// DisplayMode
If(IsBlank(galQueue.Selected), DisplayMode.Disabled, DisplayMode.Edit)
```

### btnReject (Button)

```powerfx
// Text
"✗ Reject"
```

```powerfx
// OnSelect
Patch(
    'con.document',
    galQueue.Selected,
    {
        validation_status: "Rejected",
        validated_by: User().Email,
        validated_date: DateAdd(Now(), TimeZoneOffset(), TimeUnit.Minutes)
    }
);
If(
    IsEmpty(Errors('con.document')),
    UpdateContext({locLastAction: "Entry " & Text(galQueue.Selected.entry_id) & " marked Rejected"}),
    UpdateContext({locLastAction: "FAILED: " & First(Errors('con.document')).Message})
)
```

```powerfx
// DisplayMode
If(IsBlank(galQueue.Selected), DisplayMode.Disabled, DisplayMode.Edit)
```

### lblPatchStatus (Label)

```powerfx
// Text
locLastAction
```

---

## Notes

- After a successful Patch the row no longer satisfies the gallery filter
  (`validation_status = "Unvalidated"`), so it drops out of the queue on the next
  data pull; the gallery usually refreshes itself, but you can force it by adding
  `Refresh('con.document')` after the `If(...)` in each OnSelect (costs a round
  trip).
- The Patch stamps `validated_by` with `User().Email` — the signed-in Entra user,
  matching `con.document.validated_by NVARCHAR(100)`.
- UTC conversion: `DateAdd(Now(), TimeZoneOffset(), TimeUnit.Minutes)` is the
  documented Power Fx local→UTC pattern. If you prefer to let the database own
  the timestamp entirely, an INSTEAD OF trigger or a stored procedure via Power
  Automate could stamp `SYSUTCDATETIME()`, but the client-side conversion keeps
  the app self-contained.
- Note the pipeline can undo a validation: `ingest/index_diff.py --apply` resets
  `validation_status` to `'Unvalidated'` (and nulls `validated_by`/`validated_date`)
  when a repo document changes — re-appearing queue items are by design.
- Rejected rows stay in `con.document` (nothing is deleted); they are visible in
  the Power BI completeness audit (`Rejected Documents` measure).
