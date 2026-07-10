"""Generate tests/fixtures/sample_weekly_report.pdf — a SYNTHETIC fixture.

This is NOT a real GA DCH document. It is a deterministic, reportlab-generated
stand-in for the weekly "CON Tracking Report" PDF, shaped from the report's
public description: eight lifecycle sections, each entry carrying a docket
number, applicant, project description, dates, site/county, estimated cost,
and opposition status. Replace/augment with a real DCH sample when one is
available, and re-tune the tables in ingest/weekly_report_parser.py against it.

Run from the repo root to (re)generate the committed fixture:

    python3 tests/fixtures/make_weekly_report_fixture.py

Deterministic output: the reportlab canvas is created with invariant=1 (fixed
timestamps/document ID), so regenerating produces byte-identical PDFs.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT_PATH = Path(__file__).resolve().parent / "sample_weekly_report.pdf"

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 60
TOP_Y = 745
BOTTOM_Y = 80
LINE_HEIGHT = 11

# style -> (font, size, centered)
STYLES: dict[str, tuple[str, float, bool]] = {
    "title": ("Helvetica-Bold", 13, True),
    "subtitle": ("Helvetica", 10.5, True),
    "section": ("Helvetica-Bold", 11, False),
    "rule": ("Helvetica", 9, False),
    "body": ("Helvetica", 9.5, False),
    "gap": ("Helvetica", 9.5, False),
    "continued": ("Helvetica-Oblique", 9, False),
}

PREAMBLE: list[tuple[str, str]] = [
    ("GEORGIA DEPARTMENT OF COMMUNITY HEALTH", "title"),
    ("Office of Health Planning - Certificate of Need Program", "subtitle"),
    ("CON TRACKING REPORT", "title"),
    ("Week of June 22, 2026", "subtitle"),
    ("=" * 70, "rule"),
]

CONTINUED_HEADER = "CON Tracking Report - Week of June 22, 2026 (continued)"

# (section header line, [entry line lists]). Header styles deliberately vary
# (numbering, case) to exercise the parser's tolerance; entries cover labeled
# fields, "$4.5 million" / "$1,234,567" cost forms, "Opposed by ..." status,
# LNR and DET dockets, one entry with NO docket, and both county forms
# ("County: Fulton" and "Site: Macon, Bibb County").
SECTIONS: list[tuple[str, list[list[str]]]] = [
    (
        "1. LETTERS OF INTENT",
        [
            [
                "LNR 2026-0012",
                "Applicant: Children's Healthcare of Atlanta, Inc.",
                "Project: Letter of intent to establish a pediatric ambulatory surgery center",
                "County: Fulton",
                "Estimated Cost: $9,800,000",
                "Filed: 06/15/2026",
            ],
            [
                # Deliberately docket-less entry (docket_id must parse to None).
                "Project No.: Pending assignment",
                "Applicant: Georgia Cancer Care Partners, LLC",
                "Project: Letter of intent to acquire a linear accelerator for radiation oncology",
                "County: Houston",
                "Estimated Cost: $6.2 million",
                "Filed: 06/18/2026",
            ],
            [
                "LNR-2026-0015",
                "Applicant: Tift Regional Health System, Inc.",
                # Unlabeled remainder -> project_description.
                "Letter of intent to add 12 skilled nursing beds to the existing Tifton campus.",
                "County: Tift",
                "Filed: 06/19/2026",
            ],
        ],
    ),
    (
        "2. NEW APPLICATIONS RECEIVED",
        [
            [
                "Project No.: CON-2026-0201",
                "Applicant: Coliseum Medical Centers, LLC",
                "Project: Add two ambulatory surgery operating rooms",
                "Site: Macon, Bibb County",
                "Estimated Cost: $1,234,567",
                "Opposition: None to date",
                "Filed: 6/16/26",
                "Review Period Ends: 2026-10-14",
            ],
            [
                "Project No.: CON-2026-0203",
                "Applicant: Northeast Georgia Medical Center, Inc.",
                "Project: Establish a freestanding emergency department in Braselton",
                "County: Hall",
                "Estimated Cost: $28,900,000",
                "Opposition: None to date",
                "Date Filed: June 18, 2026",
                "Decision Due: October 16, 2026",
            ],
            [
                "Project No.: CON-2026-0204",
                "Applicant: Atrium Health Floyd",
                "Project: Add an MRI unit at Floyd Medical Center",
                "County: Floyd",
                "Estimated Cost: $3.4 million",
                "Date Filed: June 19, 2026",
                "Decision Due: October 17, 2026",
            ],
        ],
    ),
    (
        "WITHDRAWN APPLICATIONS",
        [
            [
                "Project No.: CON-2025-0142",
                "Applicant: Serenity Behavioral Health Systems, LLC",
                "Project: Establish 20 adult psychiatric inpatient beds",
                "County: Columbia",
                "Estimated Cost: $8,400,000",
                "Date Filed: November 3, 2025",
                "Withdrawn: June 16, 2026",
            ],
            [
                "CON-2026-0149",
                "Applicant: Coastal Imaging Partners, LLC",
                "Project: Acquire a PET/CT scanner for a freestanding imaging center",
                "Site: Savannah, Chatham County",
                "Estimated Cost: $2,850,000",
                "Withdrawn: 06/17/2026",
            ],
        ],
    ),
    (
        "PENDING APPLICATIONS",
        [
            [
                "Project No.: CON-2026-0176",
                "Applicant: University Health Care System, Inc.",
                "Project: Relocate 24 acute-care beds within the service area",
                "County: Columbia",
                "Estimated Cost: $15,200,000",
                "Date Filed: March 9, 2026",
                "Decision Due: 07/07/2026",
            ],
            [
                "Project No.: CON-2026-0182",
                "Applicant: Hospice Savannah, Inc.",
                "Project: Expand the hospice inpatient facility by six beds",
                "County: Chatham",
                "Estimated Cost: $2.1 million",
                "Opposition: None",
                "Date Filed: March 20, 2026",
                "Decision Due: July 18, 2026",
            ],
            [
                "Project No.: CON-2026-0195",
                "Applicant: Emory Healthcare, Inc.",
                "Project: Establish an open-heart surgery program at Emory Decatur Hospital",
                "County: DeKalb",
                "Estimated Cost: $12,750,000",
                "Opposition: Opposed by Piedmont Healthcare",
                "Date Filed: April 3, 2026",
                "Decision Due: August 1, 2026",
            ],
        ],
    ),
    (
        "RECENTLY APPROVED",
        [
            [
                "Project No.: CON2026-0187",
                "Applicant: Wellstar Health System, Inc.",
                "Project: Replacement of Wellstar Spalding Regional Hospital",
                "County: SPALDING",
                "Estimated Cost: $4.5 million",
                "Opposition: None",
                "Date Filed: January 12, 2026",
                "Approved: 06/18/2026",
            ],
            [
                "CON-2025-0166",
                "Applicant: Phoebe Putney Memorial Hospital, Inc.",
                "Project: Renovate and expand the surgical services department",
                "County: Dougherty",
                "Estimated Cost: $22,000,000",
                "Approved: June 20, 2026",
            ],
        ],
    ),
    (
        "RECENTLY DENIED",
        [
            [
                "Project No.: CON-2026-0158",
                "Applicant: SurgCenter of Cherokee, LLC",
                "Project: Establish a single-specialty ambulatory surgery center",
                "County: Cherokee",
                "Estimated Cost: $5,600,000",
                "Opposition: Opposed by Northside Hospital",
                "Denied: 06/18/2026",
            ],
            [
                "Project No.: CON-2025-0171",
                "Applicant: Lakeview Behavioral Health, LLC",
                "Project: Add 16 adolescent psychiatric beds",
                "County: Gwinnett",
                "Estimated Cost: $7.25 million",
                "Denied: June 11, 2026",
            ],
        ],
    ),
    (
        "APPEALED PROJECTS",
        [
            [
                "Project No.: CON-2025-0119",
                "Applicant: Doctors Hospital of Augusta, LLC",
                "Project: Establish a burn care unit",
                "County: Richmond",
                "Estimated Cost: $14,300,000",
                "Decision Date: May 5, 2026",
                "Opposition: Appeal filed by JMS Burn Centers, Inc.",
            ],
            [
                "CON-2025-0134",
                "Applicant: Piedmont Newton Hospital, Inc.",
                "Project: Add a cardiac catheterization laboratory",
                "County: Newton",
                "Estimated Cost: $6,900,000",
                "Decision Date: April 22, 2026",
            ],
        ],
    ),
    (
        "LETTERS OF DETERMINATION",
        [
            [
                "DET2026-021",
                "Applicant: Optim Medical Center-Tattnall, LLC",
                "Project: Determination that conversion of observation beds is not reviewable",
                "County: Tattnall",
                "Decision Date: 06/19/2026",
            ],
            [
                "Docket No. DET-2026-018",
                "Applicant: PruittHealth-Augusta, LLC",
                "Project: Reviewability determination for renovation of a skilled nursing facility",
                "County: Richmond",
                "Estimated Cost: $950,000.00",
                "Decision Date: June 17, 2026",
            ],
        ],
    ),
]


def build_rows() -> list[tuple[str, str]]:
    """The whole report as (text, style) rows, in reading order."""
    rows: list[tuple[str, str]] = list(PREAMBLE)
    for header, entries in SECTIONS:
        rows.append(("", "gap"))
        rows.append((header, "section"))
        rows.append(("-" * 60, "rule"))
        for entry in entries:
            for line in entry:
                rows.append((line, "body"))
            rows.append(("", "gap"))
    return rows


def paginate(rows: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """Split rows into pages; pages after the first get a continuation header."""
    max_rows = int((TOP_Y - BOTTOM_Y) / LINE_HEIGHT)
    pages: list[list[tuple[str, str]]] = [[]]
    for row in rows:
        if len(pages[-1]) >= max_rows:
            pages.append([(CONTINUED_HEADER, "continued"), ("", "gap")])
        pages[-1].append(row)
    return pages


def render(pages: list[list[tuple[str, str]]], out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=letter, invariant=1)
    c.setTitle("CON Tracking Report - Week of June 22, 2026")
    total = len(pages)
    for number, page in enumerate(pages, start=1):
        y = TOP_Y
        for text, style in page:
            font, size, centered = STYLES[style]
            if text:
                c.setFont(font, size)
                if centered:
                    c.drawCentredString(PAGE_WIDTH / 2, y, text)
                else:
                    c.drawString(LEFT_MARGIN, y, text)
            y -= LINE_HEIGHT
        c.setFont("Helvetica", 8)
        c.drawCentredString(PAGE_WIDTH / 2, 55, f"Page {number} of {total}")
        c.showPage()
    c.save()


def main() -> None:
    pages = paginate(build_rows())
    render(pages, OUT_PATH)
    print(f"wrote {OUT_PATH} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
