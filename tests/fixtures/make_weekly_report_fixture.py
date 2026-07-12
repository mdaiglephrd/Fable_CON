"""Generate tests/fixtures/sample_weekly_report.pdf — a SYNTHETIC fixture.

This is NOT a real GA DCH document. It is a deterministic, reportlab-generated
stand-in that mimics the layout of the real weekly "CON Tracking Report"
(sample of 2026-04-21): a TOC/notices first page with the reporting period as
a date RANGE, the real section headings, empty sections marked "none", bare
year-seq CON project numbers ("2026-002", "2023013"), DET-EQT/DET-ASC/DET
determination-request entries, appealed-determination litigation narratives,
an entry spanning a page break, page numbers GLUED to the first line of each
page, and pdfplumber's lost-space quirks baked into the text ("Letters
ofIntent", "Deniedon12/6/2024", "30thDayDeadline:").

Augment/replace with a real DCH sample when one can be committed; the layout
tables in ingest/weekly_report_parser.py are tuned against the real thing.

Run from the repo root to (re)generate the committed fixture:

    python3 tests/fixtures/make_weekly_report_fixture.py

Deterministic output: the reportlab canvas is created with invariant=1 (fixed
timestamps/document ID), so regenerating produces byte-identical PDFs.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

OUT_PATH = Path(__file__).resolve().parent / "sample_weekly_report.pdf"

PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 55
TOP_Y = 750
LINE_HEIGHT = 14

# style -> (font, size)
STYLES: dict[str, tuple[str, float]] = {
    "title": ("Helvetica-Bold", 12),
    "section": ("Helvetica-Bold", 10.5),
    "body": ("Helvetica", 9),
}

# Explicit page contents: (style, text) rows. Pagination is hand-rolled so the
# page-break-spanning Appealed CON Projects entry is deterministic. Pages 2+
# get their page number GLUED to the first line (like the real PDF).
PAGES: list[list[tuple[str, str]]] = [
    # ---- Page 1: TOC / notices page (mimics the real report's cover) -------
    [
        ("body", "See the links below for easy navigation"),
        ("body", "Letters ofIntent"),
        ("body", "Letters of Intent - Expired"),
        ("body", "Letters ofIntent - Batching"),
        ("body", "New CON Applications"),
        ("body", "Withdrawn CONApplications"),
        ("body", "Pending Applications"),
        ("body", "Recently Approved CON Applications Office of Health Planning"),
        ("body", "Recently Denied CON Applications"),
        ("body", "Appealed CON Projects"),
        ("body", "Letters ofDetermination, generally"),
        ("body", "Requests for DET-EQT"),
        ("body", "Appealed Determinations"),
        ("body", "LNR Conversion"),
        ("body", "Requests for Extended"),
        ("body", "Implementation/ Performance Period"),
        ("title", "April 15, 2026 – April 21, 2026"),
        ("body", "Georgia Department of Community Health"),
        ("body", "Office of Health Planning"),
        ("body", "2 Martin Luther King Jr. Drive SE"),
        ("body", "Atlanta, Georgia 30334"),
        ("body", "https://dch.georgia.gov"),
    ],
    # ---- Page 2: LOI + application sections ---------------------------------
    [
        ("section", "IMPORTANT NOTICESLetters of Intent"),
        ("body", "LNR 2026-0012 Children's Healthcare of Atlanta, Inc."),
        ("body", "Letter ofintent toestablish apediatric ambulatory surgery center"),
        ("body", "Site: 1001 Johnson Ferry Road, Atlanta, GA30342 (Fulton County)"),
        ("body", "Filed: 4/16/2026"),
        ("body", "Project No.: Pending assignment"),
        ("body", "Applicant: Georgia Cancer Care Partners, LLC"),
        ("body", "Project: Letter of intent to acquire a linear accelerator"),
        ("body", "County: Houston"),
        ("section", "Letters of Intent – Batching"),
        ("body", "none"),
        ("section", "Expired Letters of Intent"),
        ("body", "none"),
        ("section", "New CON Applications"),
        ("body", "none"),
        ("section", "Withdrawn CON Applications"),
        ("body", "none"),
        ("section", "Pending Review Applications"),
        ("body", "2026-002 John D. Archbold Memorial Hospital, Inc."),
        ("body", "Establishment ofAdult Open Heart Surgery Service – Batching OPPOSITION FILED"),
        ("body", "Filed: 2/5/2026 Deemed Complete: 2/5/2026"),
        ("body", "30thDayDeadline: 3/6/2026"),
        ("body", "Decision Deadline: 6/4/2026"),
        ("body", "Site: 915GordonAve, Thomasville, GA31792 (Thomas County)"),
        ("body", "Contact: ChrisNewman, COO 229-228-2771"),
        ("body", "Estimated Cost: $6,945,132"),
        ("body", "2026-003 Clear Imaging, LLC"),
        ("body", "New Imaging Center inGwinnett County OPPOSITION FILED"),
        ("body", "Filed: 2/24/2026 Deemed Incomplete: 2/24/2026"),
        ("body", "30th Day Deadline: 3/25/2026"),
        ("body", "Decision Deadline: 6/23/2026"),
        ("body", "Site: 4470 Satellite Boulevard Suite 103, Duluth, GA30096 (Gwinnett County)"),
        ("body", "Contact: Daekwan Lee, President 470-546-7321"),
        ("body", "Estimated Cost: $1,015,000"),
        ("section", "Recently Approved Applications"),
        ("body", "none"),
    ],
    # ---- Page 3: appeal narratives (last entry spans onto page 4) -----------
    [
        ("section", "Recently Denied Applications"),
        ("body", "none"),
        ("section", "Disqualified Applications"),
        ("body", "none"),
        ("section", "Appealed Determinations"),
        ("body", "DET-EQT2024-073 MDS Imaging, Inc. Request forLetter ofDetermination received on 7/2/2024, regarding acquisition of"),
        ("body", "mobile MRI unit."),
        ("body", "Agency Decision: Deniedon12/6/2024"),
        ("body", "Appealed: MDS Imaging, Inc. (“MDS”) files Request forAdministrative Appeal on 1/3/2025."),
        ("body", "Hearing Officer: Dr. L. Lynn Hogue"),
        ("body", "HearingDate: N/A"),
        ("body", "Superior Court ofFulton County: Denies MDS’ Petition forJudicial Review and affirms Department’sFinal Order,"),
        ("body", "4/1/2026."),
        ("body", "DET2025-036 Crowning Moments Birth and Wellness Center, LLC Request forLetter ofDetermination received on"),
        ("body", "4/3/2025, regarding the development ofanew birthing center."),
        ("body", "Agency Decision: Approved on 5/28/2025"),
        ("body", "Appealed: Wellstar North Fulton Hospital, Inc. (“Wellstar”) files Request for Administrative Appeal on6/13/2025."),
        ("body", "HearingOfficer: MelvinM. Goldstein, Esq."),
        ("body", "HearingDate: Pending"),
        ("section", "Appealed CON Projects"),
        ("body", "2020-020 University Hospital (Columbia)"),
        ("body", "Establish aFreestanding Emergency Care Facility"),
        ("body", "Agency Decision: Approved, 7/21/2020"),
        ("body", "Appealed By: Doctors Hospital ofAugusta, LLC (“Doctors”), 8/19/2020. AU Medical"),
    ],
    # ---- Page 4: spanning-entry continuation + determination requests -------
    [
        ("body", "Center, Inc. (“AUMC”), 8/20/2020. AU Medical Center, Inc. withdraws CON 2020-023, 12/4/2024."),
        ("body", "Hearing Officer: David Will, Esq."),
        ("body", "Hearing Date: Continued untilfurthernotice"),
        ("body", "2025-009 Coliseum Medical Center, Inc. d/b/aPiedmont Macon Medical"),
        ("body", "Establish Freestanding Emergency Department"),
        ("body", "Agency Decision: Approved, 8/1/2025"),
        ("body", "Appealed By: The Medical Center ofPeach County, Inc. (“Peach”), 8/29/2025."),
        ("body", "Hearing Officer: Carl P. Dowling, Esq."),
        ("body", "Hearing Date: 8/3-7/2026, 9:30A.M. / Remote Video Conference"),
        ("section", "Requests for DET-EQT for Diagnostic or Therapeutic Equipment"),
        ("body", "DET-EQT2026002 Women'sImaging Specialists - Gwinnett, LLC"),
        ("body", "Acquisition ofMRI"),
        ("body", "Request received: 1/6/2026"),
        ("body", "Contact Person: Susan Dugger"),
        ("body", "Determination: Denied Determination Date: 4/20/2026"),
        ("body", "DET-EQT2026014 Heart and Vascular Care, Inc."),
        ("body", "Acquisition ofaCardiovascular PET/CT System"),
        ("body", "Request received: 1/13/2026"),
        ("body", "Contact Person: Everette BJenkins"),
        ("body", "Determination: Withdr/Appl Prior toDec"),
        ("body", "DateofWithdrawal: 3/27/2026"),
        ("section", "Requests for DET–ASC for Establishment of Physician-Owned"),
        ("section", "Ambulatory Surgery Facilities"),
        ("body", "(Formerly: Requests for LNR for Establishment ofPhysician-Owned Ambulatory Surgery Facilities)"),
        ("body", "DET-ASC2026001 Georgia Pain and Wellness Center, LLC d/b/aSummit Spine & Joint"),
        ("body", "Centers"),
        ("body", "Establish aSingle Specialty Ambulatory Surgery Center"),
        ("body", "Site: 8Wheeler Street, Savannah GA31405"),
        ("body", "Number ofOR's: 1 Specialty: PainMedicine"),
        ("body", "Project costsassubmitted: $982,754.66"),
        ("body", "Request received: 1/14/2026"),
        ("body", "Contact Person: Susan CAtkinson"),
        ("body", "Determination: Pending"),
    ],
    # ---- Page 5: misc determinations, extended implementation, back matter --
    [
        ("section", "Requests for Miscellaneous Letters of Determination"),
        ("body", "DET2024246 Middle Georgia Midwives"),
        ("body", "Establishment ofBirthing Center"),
        ("body", "Request received: 12/18/2024"),
        ("body", "Contact Person: Ashley Amos, CNM"),
        ("body", "Determination: Denied Determination Date: 4/6/2026"),
        ("body", "DET2026004 DouglasHospital, Inc. d/b/aWellstar Douglas MedicalCenter"),
        ("body", "MoveofHospitalOutpatient Department"),
        ("body", "Request received: 1/12/2026"),
        ("body", "Contact Person: James Satcher"),
        ("body", "Determination: Non-reviewable as proposed Determination Date: 4/15/2026"),
        ("section", "Requests for Extended Implementation/Effective Period"),
        ("body", "2023013 The Medical Center, Inc. d/b/aPiedmont Columbus Regional Midtown"),
        ("body", "Upgrade and Reconfiguration of Inpatient Beds"),
        ("body", "Request to Extend Completion Period"),
        ("body", "Site: 710 Center Street, Columbus ( Muscogee)"),
        ("body", "Project Approved: 8/18/2023"),
        ("body", "Request Received: 3/13/2026"),
        ("body", "Contact: Allen Holladay, Chief Financial Officer ( 706-660-6194)"),
        ("body", "Approved Cost: $45,840,002"),
        ("body", "Determination: Approved, 4/9/2026 Extended Mandatory Completion: July 21, 2026"),
        ("section", "Need Projection Analyses Posted 4/1/2026"),
        ("body", "2030 Non-Special MRT Need Projection – Posted 12/17/2025"),
        ("body", "2030 PET Need Projection – Posted 12/17/2025"),
        ("section", "DET Review, generally"),
        ("body", "The Office of Health Planning will no longer engage inthe review orissuance ofletters of"),
        ("body", "determination regarding freestanding facilities."),
        ("section", "LNR Conversion"),
        ("body", "AsofJune 1, 2016, the Department will nolonger engage in CON review of facilities inpossession ofanLNR."),
    ],
]


def render(pages: list[list[tuple[str, str]]], out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=letter, invariant=1)
    c.setTitle("CON Tracking Report - April 15, 2026 - April 21, 2026")
    for number, page in enumerate(pages, start=1):
        y = TOP_Y
        for row_index, (style, text) in enumerate(page):
            font, size = STYLES[style]
            if number > 1 and row_index == 0:
                # Glue the page number to the first line, like the real PDF:
                # its right edge exactly touches the line's left edge.
                page_no = str(number)
                c.setFont("Helvetica", 9)
                c.drawString(LEFT_MARGIN - stringWidth(page_no, "Helvetica", 9), y, page_no)
            c.setFont(font, size)
            c.drawString(LEFT_MARGIN, y, text)
            y -= LINE_HEIGHT
        c.showPage()
    c.save()


def main() -> None:
    render(PAGES, OUT_PATH)
    print(f"wrote {OUT_PATH} ({len(PAGES)} pages)")


if __name__ == "__main__":
    main()
