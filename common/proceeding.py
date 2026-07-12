"""Python port of tests/fixtures/handoff/docket-engine.js ``build()``.

Produces the plain-data proceeding shape the dark "case console" Docket View
renders: badge, stage groups, substeps (with tooltip content), outcome forks,
deadline callouts, compact mini-bar, and a precedent signal for closed dockets.

This module is kept in PARITY with the JS (and with web/src/lib/docketEngine.ts).
Parity is verified byte-for-byte against tests/fixtures/handoff/golden_proceeding.json
in tests/test_proceeding.py. Do not "improve" the copy — match the JS exactly,
including the middle-dot / en-dash / em-dash characters, the deterministic
precedent seed, and the en-US date formatting. Pure: no I/O.
"""

from datetime import date, timedelta

REFERENCE_NOW = date(2026, 6, 25)  # matches docket-engine.js NOW = new Date(2026, 5, 25)

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


# --- date helpers (mirror parseDate/addDays/fmt/daysBetween/durationLabel) ---


def parse_date(s) -> date | None:
    """Port of parseDate: accept a date, an "M/D/YYYY" string, or ISO; else None."""
    if not s:
        return None
    if isinstance(s, date):
        return s
    text = str(s)
    parts = text.split("/")
    if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
        m, d, y = (int(p) for p in parts)
        if len(str(y)) == 4:
            try:
                return date(y, m, d)
            except ValueError:
                return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)


def fmt(d: date | None) -> str:
    """Port of toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})."""
    if not d:
        return ""
    return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"


def days_between(a: date, b: date) -> int:
    return (b - a).days


def duration_label(a: date, b: date) -> str:
    """Port of durationLabel."""
    days = days_between(a, b)
    yrs = days // 365
    mo = round((days % 365) / 30)
    if yrs <= 0:
        return f"{mo} month" if mo == 1 else f"{mo} months"
    head = f"{yrs} yr" if yrs == 1 else f"{yrs} yrs"
    return head + (f" {mo} mo" if mo else "")


# --- deterministic precedent seed (replicates seedOf 32-bit hash) ------------


def _to_int32(n: int) -> int:
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n >= 0x80000000 else n


def seed_of(s: str) -> float:
    """Port of seedOf: h = (h*31 + charCode) | 0 ; return abs(h % 1000) / 1000."""
    h = 0
    for ch in s:
        h = _to_int32(h * 31 + ord(ch))
    return (abs(h) % 1000) / 1000


def _precedent_for_con(rec: dict, now: date) -> dict:
    s = seed_of(rec.get("num") or rec.get("facility") or "")
    if s < 0.72:
        return {
            "key": "valid",
            "label": "VALID PRECEDENT",
            "color": "#10B981",
            "bg": "rgba(16,185,129,0.12)",
            "detail": "No negative subsequent treatment found · Last reviewed "
            + fmt(add_days(now, -30)),
        }
    if s < 0.9:
        return {
            "key": "questioned",
            "label": "QUESTIONED",
            "color": "#F59E0B",
            "bg": "rgba(245,158,11,0.12)",
            "detail": "Distinguished in a subsequent proceeding · Not overruled",
        }
    return {
        "key": "overturned",
        "label": "OVERTURNED",
        "color": "#F43F5E",
        "bg": "rgba(244,63,94,0.12)",
        "detail": "Reversed or overruled on appeal · Exercise caution citing",
    }


def _precedent_for_det() -> dict:
    return {
        "key": "noprecedent",
        "label": "NO PRECEDENT",
        "color": "#94A3B8",
        "bg": "rgba(148,163,184,0.10)",
        "detail": "DET types bind parties and stated facts only — O.C.G.A. § 31-6-44 — "
        "may not be cited as authority for non-parties",
    }


def _badge_meta(dtype: str | None) -> dict:
    table = {
        "CON": {"label": "CON", "color": "#F43F5E"},
        "DET": {"label": "DET", "color": "#F59E0B"},
        "DET-ASC": {"label": "DET·ASC", "color": "#10B981"},
        "DET-EQT": {"label": "DET·EQT", "color": "#8B5CF6"},
        "LNR-ASC": {"label": "LNR·ASC", "color": "#10B981"},
        "LNR-EQT": {"label": "LNR·EQT", "color": "#8B5CF6"},
    }
    return table.get(dtype, {"label": dtype or "DKT", "color": "#94A3B8"})


# --- generic CON builder (stages 0-7) ----------------------------------------


def _build_con(rec: dict, now: date) -> dict:
    filed = parse_date(rec.get("received")) or now
    decided = parse_date(rec.get("date")) or filed
    finding = rec.get("finding") or "Pending"
    is_closed = finding != "Pending"
    elapsed = days_between(filed, decided) if is_closed else days_between(filed, now)
    denied = finding == "Denied"
    withdrawn = finding == "Withdrawn"

    d_ack = add_days(filed, 3)
    d_batch = add_days(filed, 10)
    d_notice = add_days(filed, 20)
    d_desk = decided if is_closed else add_days(filed, 120)
    d_challenge = add_days(d_desk, 14)
    d_ho_appt = add_days(d_desk, 44)
    d_sched = add_days(d_ho_appt, 9)
    d_hearing = add_days(d_sched, 90)
    d_ho_decision = add_days(d_hearing, 28)

    if is_closed:
        cur_stage = 7
    elif elapsed < 120:
        cur_stage = 1
    elif elapsed < 150:
        cur_stage = 2
    elif elapsed < 240:
        cur_stage = 3
    else:
        cur_stage = 4

    def st(n: int) -> str:
        if n < cur_stage or is_closed:
            return "complete"
        return "active" if n == cur_stage else "pending"

    stages: list[dict] = []

    stages.append({
        "n": "0",
        "status": "complete",
        "title": "Letter of Intent",
        "dateLine": "Filed " + fmt(filed),
        "substeps": [
            {"code": "0a", "label": "Submission", "tip": {
                "title": "0a · Submission", "status": "complete",
                "rows": [
                    "Letter of intent filed " + fmt(filed) + ".",
                    "Required pre-application filing — sets review cycle and batching window.",
                ],
                "statute": "O.C.G.A. § 31-6-40"}},
            {"code": "0b", "label": "Acknowledgement", "tip": {
                "title": "0b · Review Cycle / Batching", "status": "complete",
                "rows": [
                    "Acknowledged " + fmt(d_ack) + ".",
                    ("Planning service area: " + rec["county"] + " County.")
                    if rec.get("county")
                    else "Batching cycle assigned by planning service area.",
                ],
                "statute": "O.C.G.A. § 31-6-40"}},
        ],
    })

    s1status = st(1)
    stages.append({
        "n": "1",
        "status": s1status,
        "title": "Initial Filing Review",
        "dateLine": "Submitted " + fmt(filed)
        + (" · Decision " + fmt(d_desk) if is_closed else " · 120-day review clock"),
        "substeps": [
            {"code": "1a", "label": "Receipt", "tip": {
                "title": "1a · Application Submitted", "status": "complete",
                "rows": [
                    "Submitted " + fmt(filed) + ".",
                    "Filing fee paid · 120-day review clock started.",
                ],
                "statute": "O.C.G.A. § 31-6-43"}},
            {"code": "1b", "label": "Batching", "tip": {
                "title": "1b · Review Cycle / Batching", "status": "complete",
                "rows": [
                    "Batching window opened " + fmt(d_batch) + ".",
                    "Reviewed against competing applications in the same planning "
                    "service area, if any.",
                ],
                "statute": "O.C.G.A. § 31-6-43"}},
            {"code": "1c", "label": "Public Notice", "tip": {
                "title": "1c · Public Comment / Opposition", "status": "complete",
                "rows": [
                    "Notice period opened " + fmt(d_notice) + ".",
                    "Affected persons may file comments or notice of opposition.",
                ],
                "statute": "O.C.G.A. § 31-6-43"}},
            {"code": "1d", "label": "Agency Decision", "tip": {
                "title": "1d · Desk Decision",
                "status": (("denied" if denied else "complete") if is_closed else "pending"),
                "rows": (
                    [
                        "Issued " + fmt(d_desk) + " — " + finding.upper() + ".",
                        "DCH Office of Health Planning project officer of record.",
                    ]
                    if is_closed
                    else ["Due by " + fmt(d_desk) + " (120 days from filing)."]
                ),
                "statute": "O.C.G.A. § 31-6-43"}},
        ],
        "forks": [
            {"key": "approved", "label": "Approved",
             "status": "taken" if (is_closed and not denied) else "not-taken",
             "title": "Proceeds to Stage 2 (challenge window)"},
            {"key": "conditions", "label": "Approved with Conditions", "status": "not-taken",
             "title": "Conditions may include bed limits, service restrictions, or "
             "compliance reporting"},
            {"key": "denied", "label": "Denied",
             "status": "taken" if (is_closed and denied) else "not-taken",
             "title": "Proceeds to Stage 2 (challenge window)"},
        ],
    })

    stages.append({
        "n": "2",
        "status": "complete" if is_closed else st(2),
        "title": "Initial Decision Challenge",
        "dateLine": "Challenge window closed" if is_closed
        else "Opens on desk decision · 30-day window",
        "substeps": [
            {"code": "2a", "label": "Request Filed", "tip": {
                "title": "2a · Challenge Filed", "status": "complete",
                "rows": [
                    "Filed " + fmt(d_challenge)
                    + " (within 30 days of the letter of determination).",
                    "Any aggrieved party who timely intervened may request review.",
                ],
                "statute": "O.C.G.A. § 31-6-44(a)"}},
            {"code": "2b", "label": "Challenge Registered", "tip": {
                "title": "2b · Challenge Registered", "status": "complete",
                "rows": [
                    "Docketed by DCH Office of Health Planning.",
                    "Timeliness and standing screened before assignment to a hearing officer.",
                ],
                "statute": "O.C.G.A. § 31-6-44(a)"}},
        ],
        "forks": [
            {"key": "challenge", "label": "Challenge filed → proceeds", "status": "taken",
             "title": "Proceeds to Stage 3 (Administrative Appeal)"},
            {"key": "nochallenge", "label": "No challenge filed", "status": "not-taken",
             "title": "Desk decision becomes final — no further review"},
        ],
    })

    ho_denied = denied
    stages.append({
        "n": "3",
        "status": "complete" if is_closed else st(3),
        "title": "Administrative Appeal",
        "dateLine": ("Hearing " + fmt(d_hearing) + " · Decision " + fmt(d_ho_decision))
        if is_closed else ("Appointed " + fmt(d_ho_appt)),
        "substeps": [
            {"code": "3a", "label": "HO Appointed", "tip": {
                "title": "3a · Hearing Officer Appointed", "status": "complete",
                "rows": [
                    "Appointed " + fmt(d_ho_appt) + " (within 30 days of the challenge).",
                    "Assigned by the Office of State Administrative Hearings.",
                ],
                "statute": "O.C.G.A. § 31-6-44(b)"}},
            {"code": "3b", "label": "Scheduling", "tip": {
                "title": "3b · Scheduling Conference", "status": "complete",
                "rows": [
                    "Held " + fmt(d_sched) + ".",
                    "Hearing dates and discovery deadlines set.",
                ],
                "statute": "O.C.G.A. § 31-6-44(b)"}},
            {"code": "3c", "label": "Hearing Window", "tip": {
                "title": "3c · Hearing Window",
                "status": "active" if st(3) == "active" else "complete",
                "rows": [
                    "Window: 60–120 days after appointment.",
                    "Hearing dates: " + fmt(d_hearing) + ".",
                ],
                "statute": "O.C.G.A. § 31-6-44(f)"}},
            {"code": "3d", "label": "Hearing", "tip": {
                "title": "3d · Contested Case Hearing", "status": "complete",
                "rows": [
                    "Evidentiary hearing on need, financial feasibility, and access criteria.",
                    "Parties: DCH, applicant, and any intervening competing applicant.",
                ],
                "statute": "O.C.G.A. § 31-6-44(e)"}},
            {"code": "3e", "label": "HO Decision", "tip": {
                "title": "3e · Hearing Officer Decision",
                "status": "complete" if is_closed else "pending",
                "rows": (
                    [
                        "Issued " + fmt(d_ho_decision) + " — "
                        + ("Affirmed denial." if ho_denied else "Affirmed approval.")
                    ]
                    if is_closed
                    else ["Due within 30 days of hearing conclusion."]
                ),
                "statute": "O.C.G.A. § 31-6-44(e)"}},
        ],
    })

    stages.append({
        "n": "4",
        "status": "complete" if is_closed else st(4),
        "title": "Final Agency Decision",
        "dateLine": ("Effective " + fmt(d_ho_decision)) if is_closed
        else "Triggered upon Stage 3 conclusion",
        "regimeNote": {
            "current": {
                "label": "Reformed Regime (HB 1339)", "tag": "current",
                "detail": "Hearing officer decision = final agency decision. "
                "Effective 2024 · No Commissioner review."},
            "legacy": {
                "label": "Prior Regime (Pre-2024)", "tag": "legacy",
                "detail": "Optional Commissioner review · 61-day finality window."},
        },
    })

    jud_reversed = False
    stages.append({
        "n": "5",
        "status": "complete" if is_closed else st(5),
        "title": "Judicial Review",
        "dateLine": "Petition within 30 days of final agency decision",
        "substeps": [
            {"code": "5a", "label": "Petition Filed", "tip": {
                "title": "5a · Petition for Judicial Review", "status": "complete",
                "rows": [
                    "Must file within 30 days of the final agency decision.",
                    "Any party except DCH may petition · Venue: Superior Court.",
                ],
                "statute": "O.C.G.A. § 31-6-44.1"}},
            {"code": "5b", "label": "Record Transmittal", "tip": {
                "title": "5b · Record Transmittal", "status": "complete",
                "rows": [
                    "DCH must transmit the certified record and transcript within 30 "
                    "days of notice of appeal.",
                ],
                "statute": "O.C.G.A. § 31-6-44.1"}},
            {"code": "5c", "label": "Hearing on Record", "tip": {
                "title": "5c · Hearing on the Record", "status": "complete",
                "rows": [
                    "Review confined to the administrative record — no new evidence.",
                    "Deferential, substantial-evidence standard.",
                ],
                "statute": "O.C.G.A. § 50-13-19"}},
            {"code": "5d", "label": "Disposition", "tip": {
                "title": "5d · Superior Court Disposition",
                "status": "complete" if is_closed else "pending",
                "rows": [
                    "Reversed and remanded." if jud_reversed
                    else "Branch: Affirm / Reverse / Remand.",
                    "120-day default rule: if the court does not hear within 120 days of "
                    "docketing, the agency decision is affirmed by operation of law.",
                ],
                "statute": "O.C.G.A. § 31-6-44.1"}},
        ],
    })

    stages.append({
        "n": "6",
        "status": "complete" if is_closed else "pending",
        "title": "Appellate Review",
        "dateLine": "Upon Superior Court disposition",
        "substeps": [
            {"code": "6a", "label": "Court of Appeals", "tip": {
                "title": "6a · Court of Appeals",
                "status": "complete" if is_closed else "pending",
                "rows": [
                    "Either party may appeal the Superior Court order.",
                    "Branch: Affirm / Reverse / Remand.",
                ],
                "statute": "O.C.G.A. § 5-6-34"}},
            {"code": "6b", "label": "Supreme Court", "tip": {
                "title": "6b · Supreme Court of Georgia", "status": "pending",
                "rows": [
                    "By certiorari — discretionary review.",
                    "Petition for cert. granted or denied.",
                ],
                "statute": "O.C.G.A. § 5-6-15"}},
        ],
    })

    terminal_key = "withdrawn" if withdrawn else "unbuilt" if denied else "approved" if is_closed else None
    stages.append({
        "n": "7",
        "status": "complete" if is_closed else "pending",
        "title": "Terminal Outcomes",
        "dateLine": ("Record closed " + fmt(decided)) if is_closed else "",
        "terminal": [
            {"key": "approved", "label": "Approved & Conditions Pending",
             "status": "taken" if terminal_key == "approved" else "not-taken"},
            {"key": "constructed", "label": "Constructed & Licensed", "status": "not-taken"},
            {"key": "unbuilt", "label": "Withdrawn" if withdrawn else "Unbuilt / Lapsed CON",
             "status": "taken" if terminal_key in ("unbuilt", "withdrawn") else "not-taken"},
            {"key": "remanded", "label": "Remanded", "status": "not-taken"},
        ],
    })

    compact = [
        {"code": "Intent", "status": "complete"},
        {"code": "Review", "status": "active" if s1status == "pending" else "complete"},
        {"code": "Initial",
         "status": "complete" if is_closed else ("complete" if cur_stage >= 2 else "pending"),
         "tag": "Denied" if (denied and cur_stage <= 2) else None},
        {"code": "Admin",
         "status": "complete" if is_closed
         else ("active" if cur_stage == 3 else "complete" if cur_stage > 3 else "pending")},
        {"code": "Agency",
         "status": "complete" if is_closed
         else ("active" if cur_stage == 4 else "complete" if cur_stage > 4 else "pending")},
        {"code": "Superior", "status": "complete" if is_closed else "pending"},
        {"code": "Appellate", "status": "complete" if is_closed else "pending"},
        {"code": "Final", "status": "complete" if is_closed else "pending"},
    ]

    return {
        "badge": _badge_meta("CON"),
        "isClosed": is_closed,
        "isActive": not is_closed,
        "filedLine": "Filed " + fmt(filed),
        "closedLine": ("Closed " + fmt(decided)) if is_closed else None,
        "durationLine": duration_label(filed, decided) if is_closed else None,
        "finalDisposition": (
            "CON " + finding
            + (" — Affirmed through review" if denied else " — Effective " + fmt(decided))
        ) if is_closed else None,
        "precedent": _precedent_for_con(rec, now) if is_closed else None,
        "compact": compact,
        "stages": stages,
    }


# --- generic DET-family builder (stages 1-5, subtype-aware copy) --------------

_SUBTYPE_COPY = {
    "DET": {
        "label": "DET (Generic)", "sub": "Determination of Reviewability",
        "s1": "Request on DCH form + filing fee · Subject: substantial equivalent of a "
        "new institutional health service.",
        "s2": "Is this a new institutional health service? Outcomes: Reviewable / Not "
        "Reviewable / Conditioned.",
        "note": "Base type · no exemption claimed", "outcome": "CON Required",
    },
    "DET-ASC": {
        "label": "DET-ASC", "sub": "ASC Letter of Non-Reviewability",
        "s1": "$500 filing fee · Subject: proposed ambulatory surgery center operation.",
        "s2": "Does the ASC qualify as single-specialty or a qualifying joint venture? "
        "Outcomes: LNR issued / CON required.",
        "note": "Letter of Non-Reviewability (LNR)", "outcome": "LNR Issued",
    },
    "DET-EQT": {
        "label": "DET-EQT", "sub": "Equipment Threshold Determination",
        "s1": "Subject: purchase or lease of diagnostic or therapeutic equipment.",
        "s2": "HB 1339 (current): no dollar threshold — test is the new-service "
        "definition. Legacy: expenditure threshold test.",
        "note": "Anti-fragmentation: DCH aggregates component costs · era-sensitive — "
        "check docket date", "outcome": "Reviewable",
    },
    "LNR-ASC": {
        "label": "LNR-ASC", "sub": "ASC Letter of Non-Reviewability",
        "s1": "$500 filing fee · Subject: proposed ambulatory surgery center operation.",
        "s2": "Does the ASC qualify as single-specialty or a qualifying joint venture? "
        "Outcomes: LNR issued / CON required.",
        "note": "Letter of Non-Reviewability (LNR)", "outcome": "LNR Issued",
    },
    "LNR-EQT": {
        "label": "LNR-EQT", "sub": "Letter of Non-Reviewability — Equipment",
        "s1": "Subject: activity claimed exempt or outside the new-service definition.",
        "s2": "Does the activity fall within a statutory exemption or outside the "
        "new-service definition? Outcomes: LNR issued / CON required.",
        "note": "LNR may issue with operating conditions · tracking required",
        "outcome": "LNR Issued",
    },
}


def _build_det(rec: dict, now: date) -> dict:
    sub = _SUBTYPE_COPY.get(rec.get("type")) or _SUBTYPE_COPY["DET"]
    filed = parse_date(rec.get("received")) or now
    decided = parse_date(rec.get("date")) or filed
    finding = rec.get("finding") or "Pending"
    is_closed = finding != "Pending"
    elapsed = days_between(filed, decided) if is_closed else days_between(filed, now)
    not_reviewable = is_closed and (finding == "Issued")
    con_req = is_closed and not not_reviewable and finding != "Withdrawn"

    d_sufficiency = add_days(filed, 11)
    d_letter = decided if is_closed else add_days(filed, 45)
    d_challenge = add_days(d_letter, 14)
    d_ho_appt = add_days(d_letter, 44)
    d_sched = add_days(d_ho_appt, 9)
    d_hearing = add_days(d_sched, 60)
    d_ho_decision = add_days(d_hearing, 28)

    if is_closed:
        cur_stage = 5
    elif elapsed < 45:
        cur_stage = 1
    elif elapsed < 60:
        cur_stage = 2
    elif elapsed < 100:
        cur_stage = 3
    else:
        cur_stage = 4

    def st(n: int) -> str:
        if is_closed:
            return "complete"
        if n < cur_stage:
            return "complete"
        return "active" if n == cur_stage else "pending"

    stages: list[dict] = []

    stages.append({
        "n": "1",
        "status": st(1),
        "title": "Request Submission",
        "dateLine": "Filed " + fmt(filed),
        "substeps": [
            {"code": "1a", "label": "Request Filed", "tip": {
                "title": "1a · Request Filed", "status": "complete",
                "rows": [
                    "Filed " + fmt(filed) + ".",
                    sub["s1"],
                    "No letter of intent required · no review cycle or batching.",
                ],
                "statute": "O.C.G.A. § 31-6-43(e)"}},
            {"code": "1b", "label": "Subject Defined", "tip": {
                "title": "1b · Subject Defined", "status": "complete",
                "rows": [
                    sub["s1"],
                    "Classification sought: substantial equivalent of a new "
                    "institutional health service.",
                ],
                "statute": "O.C.G.A. § 31-6-2(23)"}},
            {"code": "1c", "label": "Sufficiency Screen", "tip": {
                "title": "1c · Sufficiency Screen", "status": "complete",
                "rows": [
                    "DCH administrative review of submitted information.",
                    "Sufficiency confirmed " + fmt(d_sufficiency)
                    + " · ~60-day review window begins.",
                ],
                "statute": "O.C.G.A. § 31-6-2(23)"}},
        ],
    })

    stages.append({
        "n": "2",
        "status": "complete" if is_closed else st(2),
        "title": "DCH Review & Letter Issued",
        "dateLine": ("Letter issued " + fmt(d_letter)) if is_closed
        else "Due ~60 days from filing",
        "substeps": [
            {"code": "2a", "label": "Reviewability Test", "tip": {
                "title": "2a · Reviewability Test", "status": "complete",
                "rows": [sub["s2"]],
                "statute": "O.C.G.A. § 31-6-2(23)"}},
            {"code": "2b", "label": "Letter Issued", "tip": {
                "title": "2b · Letter of Determination Issued",
                "status": "complete" if is_closed else "pending",
                "rows": (
                    ["Issued " + fmt(d_letter) + " · Outcome: " + finding.upper() + ".",
                     sub["note"]]
                    if is_closed
                    else ["Due by " + fmt(d_letter) + "."]
                ),
                "statute": "O.C.G.A. § 31-6-2(23)"}},
        ],
        "forks": [
            {"key": "notreviewable", "label": "Not Reviewable",
             "status": "taken" if not_reviewable else "not-taken",
             "title": "May proceed without CON"},
            {"key": "conditioned", "label": "Conditioned / Partial", "status": "not-taken",
             "title": "Some components reviewable, others not"},
            {"key": "reviewable", "label": "Reviewable — CON Required",
             "status": "taken" if con_req else "not-taken", "title": sub["outcome"]},
        ],
    })

    stages.append({
        "n": "3",
        "status": "complete" if is_closed else st(3),
        "title": "Finality or Challenge",
        "dateLine": "Challenge window closed" if is_closed
        else "Opens on letter issuance · 30-day window",
        "forks": [
            {"key": "challenge", "label": "Challenge Filed → Administrative Appeal",
             "status": "taken",
             "title": "Filed " + fmt(d_challenge) + " · proceeds to Stage 4"},
            {"key": "final", "label": "No Challenge Filed", "status": "not-taken",
             "title": "Letter becomes final without further review — most DETs end here"},
        ],
        "deadline": (
            {"items": [
                "Hearing officer appointment due within 30 days of challenge",
                "Hearing window: 60–120 days after appointment",
            ]}
            if (not is_closed and cur_stage == 3) else None
        ),
    })

    stages.append({
        "n": "4",
        "status": "complete" if is_closed else st(4),
        "title": "Administrative Appeal",
        "dateLine": "Identical mechanics to CON administrative appeal — HB 1339: HO "
        "decision = final agency decision",
        "substeps": [
            {"code": "4a", "label": "HO Appointed", "tip": {
                "title": "4a · Hearing Officer Appointed", "status": "complete",
                "rows": [
                    "Appointed " + fmt(d_ho_appt) + " (within 30 days of appeal filing).",
                    "Same mechanics as CON administrative appeal.",
                ],
                "statute": "O.C.G.A. § 31-6-44(b)"}},
            {"code": "4b", "label": "Scheduling", "tip": {
                "title": "4b · Scheduling Conference", "status": "complete",
                "rows": ["Held " + fmt(d_sched) + " (within 14 days of appointment)."],
                "statute": "O.C.G.A. § 31-6-44(b)"}},
            {"code": "4c", "label": "Hearing Window", "tip": {
                "title": "4c · Hearing Window",
                "status": "active" if st(4) == "active" else "complete",
                "rows": [
                    "Window: 60–120 days after filing.",
                    "Hearing set " + fmt(d_hearing) + ".",
                ],
                "statute": "O.C.G.A. § 31-6-44(f)"}},
            {"code": "4d", "label": "Hearing", "tip": {
                "title": "4d · Contested Case Hearing", "status": "complete",
                "rows": [
                    "Evidence, witnesses, and reviewability-criteria arguments.",
                    "Same format as CON hearing.",
                ],
                "statute": "O.C.G.A. § 31-6-44(e)"}},
            {"code": "4e", "label": "HO Decision", "tip": {
                "title": "4e · Hearing Officer Decision",
                "status": "complete" if is_closed else "pending",
                "rows": (
                    ["Issued " + fmt(d_ho_decision) + ".",
                     "Under HB 1339 (eff. 2024): HO decision = final agency decision."]
                    if is_closed
                    else ["Due within 30 days of hearing conclusion."]
                ),
                "statute": "O.C.G.A. § 31-6-44(e)"}},
        ],
    })

    stages.append({
        "n": "5",
        "status": "complete" if is_closed else "pending",
        "title": "Judicial & Appellate",
        "dateLine": "Upon final agency decision",
        "substeps": [
            {"code": "5a", "label": "Superior Court", "tip": {
                "title": "5 · Superior Court Petition",
                "status": "complete" if is_closed else "pending",
                "rows": [
                    "Any party except DCH may petition within 30 days of the final "
                    "agency decision.",
                    "Review on the administrative record — deferential standard.",
                    "120-day default: if no hearing within 120 days of docketing, the "
                    "agency decision is affirmed by operation of law.",
                ],
                "statute": "O.C.G.A. § 50-13-19, as modified by § 31-6-44.1"}},
            {"code": "5b", "label": "Court of Appeals", "tip": {
                "title": "5 · Court of Appeals", "status": "pending",
                "rows": [
                    "Either party may appeal the Superior Court order.",
                    "Branch: Affirm / Reverse / Remand.",
                ],
                "statute": "O.C.G.A. § 5-6-34"}},
            {"code": "5c", "label": "Supreme Court", "tip": {
                "title": "5 · Supreme Court of Georgia", "status": "pending",
                "rows": ["By certiorari — discretionary review."],
                "statute": "O.C.G.A. § 5-6-15"}},
        ],
    })

    compact = [
        {"code": "Submit", "status": "complete"},
        {"code": "Review",
         "status": "complete" if is_closed else ("active" if cur_stage <= 2 else "complete")},
        {"code": "Finality",
         "status": "complete" if is_closed
         else ("active" if cur_stage == 3 else "complete" if cur_stage > 3 else "pending")},
        {"code": "Appeal",
         "status": "complete" if is_closed
         else ("active" if cur_stage == 4 else "complete" if cur_stage > 4 else "pending")},
        {"code": "Judicial", "status": "complete" if is_closed else "pending"},
    ]

    return {
        "badge": _badge_meta(rec.get("type")),
        "subtypeLabel": sub["label"],
        "subtypeSub": sub["sub"],
        "isClosed": is_closed,
        "isActive": not is_closed,
        "filedLine": "Filed " + fmt(filed),
        "closedLine": ("Closed " + fmt(decided)) if is_closed else None,
        "durationLine": duration_label(filed, decided) if is_closed else None,
        "finalDisposition": (sub["sub"] + " — " + finding + " · " + fmt(decided))
        if is_closed else None,
        "precedent": _precedent_for_det() if is_closed else None,
        "compact": compact,
        "stages": stages,
    }


def build_proceeding(rec: dict, now: date = REFERENCE_NOW) -> dict:
    """Port of docket-engine.js build(rec): CON -> _build_con, else -> _build_det."""
    if not rec:
        return None
    return _build_con(rec, now) if rec.get("type") == "CON" else _build_det(rec, now)


# --- mapping to con.proceeding_stage rows ------------------------------------


def _stage_date(date_line: str) -> date | None:
    """Extract the first 'Mon D, YYYY' date from a stage dateLine, if any."""
    if not date_line:
        return None
    tokens = date_line.replace(",", " ").split()
    for i in range(len(tokens) - 2):
        mon, day, year = tokens[i], tokens[i + 1], tokens[i + 2]
        if mon in _MONTHS and day.isdigit() and year.isdigit() and len(year) == 4:
            try:
                return date(int(year), _MONTHS.index(mon) + 1, int(day))
            except ValueError:
                continue
    return None


def stages_to_rows(docket_id: str, proceeding: dict) -> list[dict]:
    """Map a proceeding's stages to con.proceeding_stage column dicts.

    Columns produced: docket_id, stage_num, stage_label (from title), court,
    title, stage_date (parsed from the dateLine when present), summary,
    is_current, has_opinion, sort_order.
    """
    rows: list[dict] = []
    for idx, stage in enumerate(proceeding.get("stages", [])):
        title = stage.get("title") or ""
        date_line = stage.get("dateLine") or ""
        rows.append({
            "docket_id": docket_id,
            "stage_num": stage.get("n"),
            "stage_label": title[:80],
            "court": None,
            "title": title,
            "stage_date": _stage_date(date_line),
            "summary": date_line,
            "is_current": stage.get("status") == "active",
            "has_opinion": False,
            "sort_order": idx,
        })
    return rows
