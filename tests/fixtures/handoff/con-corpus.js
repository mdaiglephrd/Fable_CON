/*
 * Georgia CON Research — data corpus
 * ----------------------------------
 * Single source of truth for case documents, dockets, citator data,
 * statutes, and rules. Replace the sample entries here with real data;
 * the UI reads everything from window.CON_CORPUS and needs no other changes.
 *
 * Paragraph / rich-text fields use a "segment" format so cross-links survive
 * in plain data (no React in this file):
 *   "plain string"                      -> text
 *   ["i", "text"]                        -> italic
 *   ["b", "text"]                        -> bold
 *   ["case", "text", "caseId"]           -> link to a case document
 *   ["stat", "text", "statuteId"]        -> link to a statute/rule section
 *   ["topic", "text", "keyId"]           -> link to a topic key number
 */
(function () {
  // disposition colors reused across dockets
  var C = {
    red: '#8E1B1F', redBg: '#FAF0F0', green: '#10B981', greenBg: '#EAF3EC',
    gold: '#F59E0B', goldBg: '#FBF1D8', gray: '#5F5950', grayBg: '#F1ECDD', neutral: '#8A8472',
  };

  // ---- Reusable docket-stage builders ----------------------------------
  function stage(o) { return o; }

  // ================= CASES =================
  var CASES = {

    // ---------- RIVERSTONE (flagship, fully authored) ----------
    'riverstone-imaging': {
      id: 'riverstone-imaging',
      badge: 'CON', dktNum: 'CON 23-0118 · now CON 2026007 (on remand)',
      captionParts: [['i', 'Riverstone Imaging, LLC'], ' v. ', ['i', 'Georgia Department of Community Health'], ', ', ['i', 'et al.']],
      tribunalLine: 'Court of Appeals of Georgia · Fifth Division · Published Opinion',
      citations: ['372 Ga. App. 488', '902 S.E.2d 144'],
      docketNo: 'No. A25A0917', decided: 'December 4, 2025', subsequent: 'Cert. denied, Mar. 12, 2026',
      treatment: { level: 'caution', word: 'Caution.', glyph: '!', bg: '#F59E0B',
        text: [' Distinguished by ', ['case', 'Three Rivers Health, LLC v. DCH', 'three-rivers'], ', 376 Ga. App. 102 (Mar. 2026), as to service-area methodology for fixed MRI applications.'] },
      editorial: "Court of Appeals affirmed the Superior Court's reversal of the Department of Community Health's denial of a fixed-MRI certificate of need to Riverstone Imaging. Held: (1) the Department's adoption of a five-county service area, in disregard of record evidence that 78% of historical referrals originated from a three-county primary service area, was not supported by substantial evidence; (2) the proper inquiry under Rule 111-2-2-.40 requires the agency to consider, as a starting point, the applicant's demonstrated referral patterns; (3) remand to the Department for application of a corrected service-area methodology.",
      headnotes: [
        { num: '1', key: 'CON VI · 24', keyId: 'vi-24', topic: 'Substantial Evidence — Standard of Review', text: 'Judicial review of a final agency decision under O.C.G.A. § 31-6-44.1 is confined to whether the decision is supported by substantial evidence in the record as a whole. While the court must defer to the agency on factual determinations within its expertise, the deference does not extend to a methodology that disregards uncontroverted record evidence of historical referral patterns.' },
        { num: '2', key: 'CON III · 7', keyId: 'iii-7', topic: 'Need / Utilization — Service Area Methodology', text: 'Under Ga. Comp. R. & Regs. 111-2-2-.40, the Department\u2019s identification of a service area for a fixed MRI application must, at a minimum, account for the applicant\u2019s demonstrated referral patterns. An agency definition that aggregates counties solely on geographic-contiguity grounds, without reference to actual patient travel patterns, is arbitrary as applied.' },
        { num: '3', key: 'CON VI · 25', keyId: 'vi-25', topic: 'Final Agency Action — Remand', text: 'Where an agency\u2019s final decision rests on a methodology unsupported by substantial evidence, the proper remedy is reversal and remand for application of a corrected methodology, not for the reviewing court to substitute its own service-area determination.' },
      ],
      byline: 'PIPKIN, Judge.',
      intro: 'Riverstone Imaging, LLC ("Riverstone") appeals from the final order of the Department of Community Health (the "Department") denying its application for a certificate of need ("CON") to establish a fixed magnetic resonance imaging service in Bartow County. The Superior Court of Fulton County reversed and remanded; the Department and intervenor Three Rivers Health, LLC, appeal. For the reasons that follow, we affirm.',
      paragraphs: [
        { num: '1', segs: ['In February 2023, Riverstone Imaging filed a letter of intent and, in March 2023, a CON application under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' seeking to establish a fixed 1.5-Tesla magnetic resonance imaging service in Cartersville, Bartow County. The application defined the proposed primary service area ("PSA") as Bartow, Gordon, and Floyd Counties, supported by referral-data from twelve area orthopedic, neurology, and primary-care groups, which demonstrated that 78 percent of MRI orders from the proposed referral base originated from those three counties.'] },
        { num: '2', segs: ['The Department, in its initial decision of June 30, 2023, redefined the service area to a five-county aggregation (Bartow, Gordon, Floyd, Polk, and Paulding) and concluded, applying ', ['stat', 'Rule 111-2-2-.40(4)(b)', 'rule-111-2-2-.40'], ', that the existing fixed unit at Cartersville Medical Center was operating below the 6,000-procedure utilization threshold. On that basis, the application was denied for failure to demonstrate unmet need.'] },
        { num: '3', segs: ['Riverstone timely sought administrative review pursuant to ', ['stat', 'O.C.G.A. § 31-6-44(c)', '31-6-44'], '. After a four-day evidentiary hearing in October 2023, the Hearing Officer issued an initial decision on February 14, 2024, affirming the Department. The Commissioner adopted the initial decision in a final order dated August 7, 2024. Riverstone timely petitioned the Superior Court of Fulton County for judicial review under ', ['stat', 'O.C.G.A. § 31-6-44.1', '31-6-44.1'], '.'] },
        { num: '4', segs: ['On March 18, 2025, the Superior Court reversed and remanded, holding that the Department\u2019s service-area definition was unsupported by substantial evidence in light of the unrebutted referral data of record. The Department and Three Rivers Health, LLC — which had intervened as a competing applicant — appealed.'] },
        { num: '5', segs: [['b', '1. Standard of review. '], 'We review a superior court\u2019s order on judicial review of a CON decision for legal error and apply the substantial-evidence test to the agency\u2019s underlying findings. ', ['case', 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC', 'coastal-empire'], ', 358 Ga. App. 211, 213 (2023); see also ', ['stat', 'O.C.G.A. § 50-13-19(h)', '50-13-19'], '. Substantial evidence is "such relevant evidence as a reasonable mind might accept as adequate to support a conclusion." ', ['i', 'Id.'], ' at 214.'] },
        { num: '6', segs: [['b', '2. Service-area methodology. '], 'The crux of this appeal is the Department\u2019s service-area determination. We have previously held that the agency\u2019s definition of a service area, while owed deference, must rest on a methodology consonant with the record. ', ['case', 'Coastal Empire', 'coastal-empire'], ', 358 Ga. App. at 217. The five-county aggregation adopted here is not so consonant. The record reflects, without contradiction, that 78 percent of referrals from Riverstone\u2019s proposed referral base originated from a three-county area. The Department offered no expert testimony, no internal study, and no record evidence explaining the rationale for adding Polk and Paulding Counties beyond geographic contiguity.'] },
        { num: '7', segs: ['We do not hold today that geographic contiguity is irrelevant; we hold only that a methodology that begins and ends with contiguity, in disregard of unrebutted referral data, is not supported by substantial evidence as applied to this record. The Department remains free, on remand, to defend a corrected service-area determination by reference to record evidence — but the choice of methodology must be reasoned, not reflexive.'] },
        { num: '8', segs: [['b', '3. Remedy. '], 'The proper remedy is remand for application of a corrected methodology consistent with this opinion. We decline the appellees\u2019 invitation to enter judgment granting the CON; that determination, in the first instance, belongs to the Department. See ', ['stat', 'O.C.G.A. § 31-6-44.1(b)', '31-6-44.1'], '.'] },
      ],
      disposition: [['b', 'Judgment affirmed.'], ' ', ['i', 'McFadden, P.J., and Brown, J., concur.']],
      meta: { Service: 'Fixed MRI (1.5T)', Applicant: 'Riverstone Imaging, LLC', County: 'Bartow County (PSA: Bartow, Gordon, Floyd)', 'CON No.': '23-0118', Intervenor: 'Three Rivers Health, LLC', Argued: 'Sept. 9, 2025' },
      counsel: [
        { role: 'For Appellee Riverstone', name: 'Andrew T. Halverson', firm: 'Parker, Hudson, Rainer & Dobbs LLP' },
        { role: 'For Appellant Department', name: 'Carrie A. Hanlon', firm: 'Senior Assistant A.G.' },
        { role: 'For Intervenor Three Rivers', name: 'Stephen P. Maddox', firm: 'Maddox & Wexler' },
      ],
      docketDays: '1,124 days', docketDispositions: 8,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed', cite: 'CON No. 23-0118', date: 'Mar. 1, 2023', outcome: 'Filed', oc: 'gray', marker: 'open', summary: 'Application to establish a fixed 1.5T MRI service in Bartow County. PSA defined as Bartow, Gordon, Floyd Counties (3-county). Twelve referral letters submitted.', filingsCount: 14, judge: 'M. Patel, Planning Officer' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Application Denied', cite: 'DCH Init. Dec. (Jun. 30, 2023)', date: 'Jun. 30, 2023', outcome: 'Denied', oc: 'red', marker: 'red', summary: 'Department redefined PSA to 5-county aggregation. Need analysis under Rule 111-2-2-.40(4)(b) found existing fixed unit at Cartersville Medical Center below utilization threshold.', filingsCount: 3, judge: 'M. Patel, Planning Officer', duration: '121 days', hasOpinion: true }),
        stage({ stageNum: '03', stageLabel: 'Hearing', court: 'Office of State Administrative Hearings', title: 'OSAH Initial Decision — Affirmed Denial', cite: 'OSAH-DCH-CON-23-118-Walsh', date: 'Feb. 14, 2024', outcome: 'Affirmed', oc: 'gray', marker: 'gray', summary: '4-day evidentiary hearing (Oct. 23\u201326, 2023). Hearing Officer Walsh affirmed the Department\u2019s service-area methodology, finding it within the agency\u2019s discretion under § 31-6-43.', filingsCount: 22, judge: 'Walsh, ALJ', duration: '229 days', hasOpinion: true }),
        stage({ stageNum: '04', stageLabel: 'Final Agency Decision', court: 'DCH Commissioner', title: 'Commissioner Final Order — Affirmed', cite: 'DCH Final Order 24-118 (Aug. 7, 2024)', date: 'Aug. 7, 2024', outcome: 'Affirmed', oc: 'gray', marker: 'gray', summary: 'Commissioner Murray adopted the Hearing Officer\u2019s initial decision in full as the final agency decision. Constitutes final agency action under O.C.G.A. § 31-6-44.1.', filingsCount: 4, judge: 'Caylee Murray, Commissioner', duration: '175 days', hasOpinion: true }),
        stage({ stageNum: '05', stageLabel: 'Judicial Review', court: 'Superior Court of Fulton County', title: 'Reversed and Remanded', cite: 'No. 2024CV-3318', date: 'Mar. 18, 2025', outcome: 'Reversed', oc: 'gold', marker: 'gold', summary: 'Held: Department\u2019s service-area determination unsupported by substantial evidence in light of unrebutted referral data. Remanded for application of corrected methodology.', filingsCount: 31, judge: 'Welch, J.', duration: '193 days', hasOpinion: true, connectorRed: true }),
        stage({ stageNum: '06', stageLabel: 'Appeal', court: 'Court of Appeals of Georgia', title: 'Affirmed Superior Court', cite: '372 Ga. App. 488, 902 S.E.2d 144', date: 'Dec. 4, 2025', outcome: 'Affirmed', oc: 'green', marker: 'green', summary: 'Pipkin, J., for the Court (5th Div., McFadden, P.J., and Brown, J., concurring). Affirmed reversal. Service-area methodology must, at a minimum, account for demonstrated referral patterns.', filingsCount: 17, judge: 'Pipkin, J.', duration: '261 days', isCurrent: true, hasOpinion: true, opinionSelf: true }),
        stage({ stageNum: '07', stageLabel: 'Cert Petition', court: 'Supreme Court of Georgia', title: 'Petition for Certiorari Denied', cite: 'No. S26C0411', date: 'Mar. 12, 2026', outcome: 'Cert Denied', oc: 'gray', marker: 'gray', summary: 'Petition by Department and intervenor Three Rivers Health denied without opinion. Court of Appeals opinion stands as binding precedent.', filingsCount: 6, judge: 'Per curiam', duration: '98 days' }),
        stage({ stageNum: '08', stageLabel: 'Remand', court: 'DCH Planning Section', title: 'Proceedings on Remand — Pending', cite: 'CON No. 23-0118 (on remand)', date: 'Apr. 8, 2026', outcome: 'Pending', oc: 'gold', marker: 'goldOpen', summary: 'Department to re-evaluate the application under a corrected service-area methodology. Initial supplemental record due by Jun. 30, 2026.', filingsCount: 2, judge: 'M. Patel, Planning Officer', duration: '78 days (open)', last: true }),
      ],
      chrono: [
        ['08', 'Apr', '2026', 'Filing · Applicant', 'gray', 'Notice of Remand Status Report filed', 'Riverstone Imaging, LLC'],
        ['12', 'Mar', '2026', 'Order · Ga. Sup. Ct.', 'gray', 'Petition for Certiorari DENIED', 'Per curiam — Cert. Den.'],
        ['06', 'Feb', '2026', 'Brief', 'gray', 'Brief in Opposition to Cert. Petition', 'Riverstone Imaging, LLC'],
        ['05', 'Jan', '2026', 'Filing · Petitioner', 'gray', 'Petition for Writ of Certiorari', 'Ga. Dep\u2019t of Cmty. Health'],
        ['04', 'Dec', '2025', 'Opinion · Ct. App.', 'green', 'OPINION — Judgment Affirmed', 'Pipkin, J., for Fifth Division'],
        ['09', 'Sep', '2025', 'Hearing', 'gray', 'Oral Argument held', 'Ct. App., Fifth Division'],
        ['22', 'Jul', '2025', 'Brief', 'gray', 'Appellee\u2019s Brief filed', 'Riverstone Imaging, LLC'],
        ['30', 'May', '2025', 'Brief', 'gray', 'Appellant\u2019s Brief filed', 'Ga. Dep\u2019t of Cmty. Health'],
        ['15', 'Apr', '2025', 'Filing', 'gray', 'Notice of Appeal filed', 'Ga. Dep\u2019t of Cmty. Health'],
        ['18', 'Mar', '2025', 'Order · Sup. Ct.', 'gold', 'ORDER — Reversed and Remanded', 'Welch, J.'],
        ['14', 'Jan', '2025', 'Hearing', 'gray', 'Oral Argument held', 'Fulton Sup. Ct.'],
        ['20', 'Nov', '2024', 'Brief', 'gray', 'Respondent\u2019s Brief filed', 'Ga. Dep\u2019t of Cmty. Health'],
        ['06', 'Sep', '2024', 'Filing', 'gray', 'Petition for Judicial Review filed', 'Riverstone Imaging, LLC'],
        ['07', 'Aug', '2024', 'Order · DCH', 'gray', 'FINAL ORDER — Affirmed Hearing Officer', 'Comm\u2019r Caylee Murray'],
        ['01', 'Mar', '2024', 'Filing', 'gray', 'Petition for Commissioner Review', 'Riverstone Imaging, LLC'],
        ['14', 'Feb', '2024', 'Order · OSAH', 'gray', 'INITIAL DECISION — Affirmed Denial', 'Walsh, ALJ'],
        ['26', 'Oct', '2023', 'Hearing', 'gray', 'Day 4 — Closing arguments', 'Walsh, ALJ'],
        ['23', 'Oct', '2023', 'Hearing', 'gray', 'Day 1 — Evidentiary hearing begins', 'Walsh, ALJ'],
        ['14', 'Jul', '2023', 'Filing', 'gray', 'Request for Administrative Hearing', 'Riverstone Imaging, LLC'],
        ['30', 'Jun', '2023', 'Order · DCH', 'red', 'INITIAL DECISION — Application Denied', 'M. Patel, Planning Officer'],
        ['12', 'Apr', '2023', 'Hearing', 'gray', 'Public Hearing — Bartow County', 'DCH Planning Section'],
        ['01', 'Mar', '2023', 'Filing', 'gray', 'CON Application filed', 'Riverstone Imaging, LLC'],
        ['15', 'Jan', '2023', 'Filing', 'gray', 'Letter of Intent filed', 'Riverstone Imaging, LLC'],
      ],
      briefs: [
        { title: 'Brief of Appellee Riverstone Imaging, LLC', meta: 'Filed Jul. 22, 2025 · Andrew T. Halverson, Parker, Hudson, Rainer & Dobbs LLP · 48 pp.' },
        { title: 'Brief of Appellant Ga. Dep\u2019t of Community Health', meta: 'Filed May 30, 2025 · Carrie A. Hanlon, Sr. Asst. A.G. · 41 pp.' },
        { title: 'Brief of Intervenor-Appellant Three Rivers Health, LLC', meta: 'Filed May 30, 2025 · Stephen P. Maddox, Maddox & Wexler · 36 pp.' },
        { title: 'Reply Brief of Appellants', meta: 'Filed Aug. 12, 2025 · 18 pp.' },
        { title: 'Amicus Brief — Georgia Alliance of Community Hospitals', meta: 'Filed Jun. 9, 2025 · 22 pp.' },
      ],
      citator: {
        flags: [ { label: 'Citing', count: 27, color: '#141414' }, { label: 'Positive', count: 19, color: '#10B981' }, { label: 'Cautionary', count: 5, color: '#F59E0B' }, { label: 'Negative', count: 3, color: '#8E1B1F' } ],
        cases: [
          { badge: 'CON', dktNum: 'CON 2026004', treat: 'Distinguished', level: 'caution', title: 'Three Rivers Health, LLC v. DCH', cite: '376 Ga. App. 102 (2026)', depth: 3, snippet: 'Distinguishing Riverstone on the ground that the competing applicant had stipulated to the five-county service area at the hearing stage.', keys: [['CON III·7', 'iii-7']], target: 'three-rivers' },
          { badge: 'CON', dktNum: 'No. 2024CV-3318', treat: 'Followed', level: 'positive', title: 'Magnolia Behavioral Health, LLC v. DCH', cite: 'Fulton Super. Ct. (2024)', depth: 4, snippet: 'Following Riverstone; population-based methodology that ignores existing-provider occupancy data fails substantial-evidence review.', keys: [['CON VI·24', 'vi-24']], target: 'magnolia' },
          { badge: 'CON', dktNum: 'OSAH-DCH-CON-25-018', treat: 'Followed', level: 'positive', title: 'Cobblestone Surgical Partners, LLC v. DCH', cite: 'OSAH (2025)', depth: 2, snippet: 'Citing Riverstone for the proposition that service-area definition must account for referral patterns.', keys: [['CON IV·13', 'iv-13']], target: 'cobblestone' },
        ],
        toa: [
          { title: 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC', cite: '358 Ga. App. 211 (2023)', pinpoint: 'pp. 213-217', target: 'coastal-empire', kind: 'case' },
          { title: 'O.C.G.A. § 31-6-44.1 — Judicial Review', cite: 'Ga. Code Ann.', pinpoint: 'subsection (b)', target: '31-6-44.1', kind: 'stat' },
          { title: 'O.C.G.A. § 31-6-43 — Granting or Denying CON', cite: 'Ga. Code Ann.', pinpoint: 'subsection (a)', target: '31-6-43', kind: 'stat' },
          { title: 'Ga. Comp. R. & Regs. 111-2-2-.40 — MRI Need Methodology', cite: 'Ga. Comp. R. & Regs.', pinpoint: '(4)(b)', target: 'rule-111-2-2-.40', kind: 'stat' },
        ],
      },
    },

    // ---------- MAGNOLIA ----------
    'magnolia': {
      id: 'magnolia', badge: 'CON', dktNum: 'CON 2026004',
      captionParts: [['i', 'Magnolia Behavioral Health, LLC'], ' v. ', ['i', 'Georgia Department of Community Health']],
      tribunalLine: 'Superior Court of Fulton County · Order on Judicial Review',
      citations: ['No. 2024CV-3318'], docketNo: 'No. 2024CV-3318', decided: 'November 21, 2024', subsequent: 'Appeal docketed, Ga. Ct. App. (pending)',
      treatment: { level: 'caution', word: 'Caution.', glyph: '!', bg: '#F59E0B', text: [' Limited holding — reversed and remanded on the psychiatric-bed need methodology only. Appeal pending.'] },
      editorial: 'Superior Court reversed and remanded the Department\u2019s denial of a CON for 48 psychiatric beds. Held: a population-based need methodology that does not reference the actual occupancy data of existing psychiatric providers in the service area fails the substantial-evidence standard. Following Riverstone Imaging.',
      headnotes: [
        { num: '1', key: 'CON IV · 11', keyId: 'iv-11', topic: 'Psychiatric / Behavioral — Need', text: 'A population-ratio need methodology for psychiatric beds, applied without regard to the documented occupancy of existing providers in the service area, does not satisfy the substantial-evidence standard under O.C.G.A. § 31-6-44.1.' },
        { num: '2', key: 'CON VI · 24', keyId: 'vi-24', topic: 'Substantial Evidence', text: 'Where uncontroverted record evidence shows existing providers operating above 90% occupancy, an agency finding of "no unmet need" premised solely on a statewide bed-to-population ratio is clearly erroneous.' },
      ],
      byline: 'WELCH, Judge.',
      intro: 'Magnolia Behavioral Health, LLC petitions for judicial review of the Department of Community Health\u2019s final decision denying its application for a certificate of need to establish 48 psychiatric beds serving Fulton and DeKalb Counties. For the reasons below, the decision is reversed and the matter remanded.',
      paragraphs: [
        { num: '1', segs: ['Magnolia applied under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' to establish a 48-bed adult psychiatric facility. The Department denied the application, finding no unmet need under the bed-to-population ratio set out in ', ['stat', 'Rule 111-2-2', 'rule-111-2-2'], '.'] },
        { num: '2', segs: ['The record reflects that the three existing psychiatric providers in the proposed service area operated at a combined 92% occupancy over the preceding twelve months, with documented diversion events. The Department\u2019s analysis did not address this occupancy data.'] },
        { num: '3', segs: [['b', 'Need methodology. '], 'As the Court of Appeals recently held in ', ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'], ', 372 Ga. App. 488 (2025), an agency need determination must engage the record evidence before it. A ratio untethered from existing-provider utilization cannot, on this record, supply substantial evidence of "no need."'] },
        { num: '4', segs: ['The matter is remanded for the Department to evaluate need with reference to the occupancy and diversion data of record. The Court expresses no view on the ultimate merits of the application.'] },
      ],
      disposition: [['b', 'Reversed and remanded.']],
      meta: { Service: 'Psychiatric Beds (48)', Applicant: 'Magnolia Behavioral Health, LLC', County: 'DeKalb (PSA: Fulton, DeKalb)', 'CON No.': '2026004', Petitioner: 'Magnolia Behavioral Health, LLC', Decided: 'Nov. 21, 2024' },
      counsel: [
        { role: 'For Petitioner Magnolia', name: 'Dana R. Whitfield', firm: 'Parker, Hudson, Rainer & Dobbs LLP' },
        { role: 'For Respondent Department', name: 'Carrie A. Hanlon', firm: 'Senior Assistant A.G.' },
      ],
      docketDays: '612 days', docketDispositions: 5,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed', cite: 'CON 2026004', date: 'Feb. 4, 2026', outcome: 'Filed', oc: 'gray', marker: 'open', summary: '48 adult psychiatric beds, Fulton/DeKalb PSA.', filingsCount: 11, judge: 'C. MacEwen, Planning Officer' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Denied', cite: 'DCH Init. Dec. (Apr. 14, 2026)', date: 'Apr. 14, 2026', outcome: 'Denied', oc: 'red', marker: 'red', summary: 'Denied on population-ratio need methodology; existing-provider occupancy not addressed.', filingsCount: 3, judge: 'C. MacEwen', duration: '69 days', hasOpinion: true }),
        stage({ stageNum: '03', stageLabel: 'Judicial Review', court: 'Superior Court of Fulton County', title: 'Reversed and Remanded', cite: 'No. 2024CV-3318', date: 'Nov. 21, 2024', outcome: 'Reversed', oc: 'gold', marker: 'gold', summary: 'Population methodology that ignores occupancy data fails substantial-evidence review. Following Riverstone.', filingsCount: 19, judge: 'Welch, J.', duration: '221 days', hasOpinion: true, opinionSelf: true, last: true }),
      ],
      chrono: [
        ['21', 'Nov', '2024', 'Order · Sup. Ct.', 'gold', 'ORDER — Reversed and Remanded', 'Welch, J.'],
        ['14', 'Apr', '2026', 'Order · DCH', 'red', 'INITIAL DECISION — Denied', 'C. MacEwen'],
        ['04', 'Feb', '2026', 'Filing', 'gray', 'CON Application filed', 'Magnolia Behavioral Health, LLC'],
      ],
      briefs: [
        { title: 'Petitioner\u2019s Brief on Judicial Review', meta: 'Dana R. Whitfield, Parker, Hudson, Rainer & Dobbs LLP · 38 pp.' },
        { title: 'Respondent Department\u2019s Brief', meta: 'Carrie A. Hanlon, Sr. Asst. A.G. · 31 pp.' },
      ],
      citator: {
        flags: [ { label: 'Citing', count: 6, color: '#141414' }, { label: 'Positive', count: 4, color: '#10B981' }, { label: 'Cautionary', count: 2, color: '#F59E0B' }, { label: 'Negative', count: 0, color: '#8E1B1F' } ],
        cases: [
          { badge: 'CON', dktNum: '—', treat: 'Followed', level: 'positive', title: 'In re Lakeview Psychiatric Pavilion', cite: 'DCH (2026)', depth: 2, snippet: 'Applying Magnolia; occupancy data of existing providers is a required input to the psychiatric-bed need analysis.', keys: [['CON IV·11', 'iv-11']], target: null },
        ],
        toa: [
          { title: 'Riverstone Imaging, LLC v. DCH', cite: '372 Ga. App. 488 (2025)', pinpoint: 'pp. 214-217', target: 'riverstone-imaging', kind: 'case' },
          { title: 'O.C.G.A. § 31-6-44.1 — Judicial Review', cite: 'Ga. Code Ann.', pinpoint: 'subsection (b)', target: '31-6-44.1', kind: 'stat' },
        ],
      },
    },

    // ---------- COASTAL EMPIRE ----------
    'coastal-empire': {
      id: 'coastal-empire', badge: 'CON', dktNum: 'CON 21-0044',
      captionParts: [['i', 'Coastal Empire Hospital Authority'], ' v. ', ['i', 'Piedmont Coastal Health, LLC']],
      tribunalLine: 'Court of Appeals of Georgia · Second Division · Published Opinion',
      citations: ['358 Ga. App. 211', '854 S.E.2d 718'], docketNo: 'No. A23A1187', decided: 'October 19, 2023', subsequent: 'Cert. denied, Feb. 6, 2024',
      treatment: { level: 'positive', word: 'Positive.', glyph: '\u2713', bg: '#10B981', text: [' No negative subsequent history. Followed by ', ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'], ', 372 Ga. App. 488 (2025).'] },
      editorial: 'Court of Appeals affirmed the grant of a CON for hospital beds, holding that the proper need methodology must take into account demonstrated referral patterns and record evidence of cross-county patient flow. The seminal statement of the service-area principle later applied in Riverstone.',
      headnotes: [
        { num: '1', key: 'CON IV · 12', keyId: 'iv-12', topic: 'Hospital Beds — Need', text: 'A need methodology for hospital beds must account for the demonstrated referral patterns and record evidence of cross-county patient flow; Rule 111-2-2 does not require a hyper-mechanical application divorced from market reality.' },
        { num: '2', key: 'CON VI · 24', keyId: 'vi-24', topic: 'Substantial Evidence', text: 'An agency determination supported by referral-pattern evidence and existing-provider utilization data satisfies the substantial-evidence standard and is entitled to deference on judicial review.' },
      ],
      byline: 'BARNES, Presiding Judge.',
      intro: 'Coastal Empire Hospital Authority appeals from the Department\u2019s grant of a certificate of need to Piedmont Coastal Health, LLC, for additional acute-care beds. We affirm.',
      paragraphs: [
        { num: '1', segs: ['Piedmont Coastal applied under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' for additional acute-care beds, defining a service area based on documented cross-county referral patterns from a four-county region.'] },
        { num: '2', segs: ['The Department granted the application. Coastal Empire, an existing provider, sought review, arguing the service area was improperly drawn.'] },
        { num: '3', segs: [['b', 'Need methodology. '], 'The proper need methodology must, at a minimum, take into account the demonstrated referral patterns and the substantial evidence in the record of cross-county patient flow. ', ['stat', 'Rule 111-2-2', 'rule-111-2-2'], ' does not require a hyper-mechanical application divorced from market reality.'] },
        { num: '4', segs: ['Because the Department\u2019s determination rested on referral-pattern and utilization evidence of record, it is supported by substantial evidence and entitled to deference.'] },
      ],
      disposition: [['b', 'Judgment affirmed.'], ' ', ['i', 'Miller and Brown, JJ., concur.']],
      meta: { Service: 'Hospital Beds (Acute Care)', Applicant: 'Piedmont Coastal Health, LLC', County: 'Chatham (4-county PSA)', 'CON No.': '21-0044', Appellant: 'Coastal Empire Hospital Authority', Argued: 'Aug. 15, 2023' },
      counsel: [
        { role: 'For Appellee Piedmont Coastal', name: 'Stephen P. Maddox', firm: 'Maddox & Wexler' },
        { role: 'For Appellant Coastal Empire', name: 'Andrew T. Halverson', firm: 'Parker, Hudson, Rainer & Dobbs LLP' },
      ],
      docketDays: '892 days', docketDispositions: 5,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed', cite: 'CON 21-0044', date: 'Jan. 12, 2021', outcome: 'Filed', oc: 'gray', marker: 'open', summary: 'Additional acute-care beds; four-county PSA from referral patterns.', filingsCount: 16, judge: 'T. Branch, Planning Officer' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Granted', cite: 'DCH Init. Dec. (2021)', date: 'May 11, 2021', outcome: 'Granted', oc: 'green', marker: 'green', summary: 'Granted on referral-pattern need analysis.', filingsCount: 4, judge: 'T. Branch', duration: '119 days', hasOpinion: true }),
        stage({ stageNum: '03', stageLabel: 'Hearing', court: 'OSAH', title: 'Initial Decision — Affirmed Grant', cite: 'OSAH-DCH-CON-21-044', date: 'Jan. 30, 2022', outcome: 'Affirmed', oc: 'gray', marker: 'gray', summary: 'Competitor challenge to service area rejected.', filingsCount: 20, judge: 'Kennedy, ALJ', duration: '264 days', hasOpinion: true }),
        stage({ stageNum: '04', stageLabel: 'Appeal', court: 'Court of Appeals of Georgia', title: 'Affirmed Grant of CON', cite: '358 Ga. App. 211', date: 'Oct. 19, 2023', outcome: 'Affirmed', oc: 'green', marker: 'green', summary: 'Service-area methodology must account for referral patterns. Seminal statement of the principle.', filingsCount: 18, judge: 'Barnes, P.J.', duration: '320 days', isCurrent: true, hasOpinion: true, opinionSelf: true, last: true }),
      ],
      chrono: [
        ['19', 'Oct', '2023', 'Opinion · Ct. App.', 'green', 'OPINION — Judgment Affirmed', 'Barnes, P.J.'],
        ['15', 'Aug', '2023', 'Hearing', 'gray', 'Oral Argument held', 'Ct. App., Second Division'],
        ['30', 'Jan', '2022', 'Order · OSAH', 'gray', 'INITIAL DECISION — Affirmed Grant', 'Kennedy, ALJ'],
        ['11', 'May', '2021', 'Order · DCH', 'green', 'INITIAL DECISION — Granted', 'T. Branch'],
        ['12', 'Jan', '2021', 'Filing', 'gray', 'CON Application filed', 'Piedmont Coastal Health, LLC'],
      ],
      briefs: [
        { title: 'Brief of Appellee Piedmont Coastal Health, LLC', meta: 'Stephen P. Maddox, Maddox & Wexler · 44 pp.' },
        { title: 'Brief of Appellant Coastal Empire Hospital Authority', meta: 'Andrew T. Halverson, Parker, Hudson, Rainer & Dobbs LLP · 39 pp.' },
      ],
      citator: {
        flags: [ { label: 'Citing', count: 41, color: '#141414' }, { label: 'Positive', count: 34, color: '#10B981' }, { label: 'Cautionary', count: 5, color: '#F59E0B' }, { label: 'Negative', count: 2, color: '#8E1B1F' } ],
        cases: [
          { badge: 'CON', dktNum: '372 Ga. App. 488', treat: 'Followed', level: 'positive', title: 'Riverstone Imaging, LLC v. DCH', cite: '372 Ga. App. 488 (2025)', depth: 4, snippet: 'Following Coastal Empire; the agency must engage referral-pattern evidence when defining a service area.', keys: [['CON III·7', 'iii-7']], target: 'riverstone-imaging' },
          { badge: 'CON', dktNum: 'OSAH-DCH-CON-25-018', treat: 'Followed', level: 'positive', title: 'Cobblestone Surgical Partners, LLC v. DCH', cite: 'OSAH (2025)', depth: 3, snippet: 'Coastal Empire requires consideration of physician practice patterns in defining an ASC service area.', keys: [['CON IV·13', 'iv-13']], target: 'cobblestone' },
        ],
        toa: [
          { title: 'O.C.G.A. § 31-6-43 — Granting or Denying CON', cite: 'Ga. Code Ann.', pinpoint: 'subsection (a)', target: '31-6-43', kind: 'stat' },
          { title: 'Ga. Comp. R. & Regs. 111-2-2 — CON Rules', cite: 'Ga. Comp. R. & Regs.', pinpoint: 'generally', target: 'rule-111-2-2', kind: 'stat' },
        ],
      },
    },

    // ---------- THREE RIVERS ----------
    'three-rivers': {
      id: 'three-rivers', badge: 'CON', dktNum: 'CON 23-0118 (companion)',
      captionParts: ['In re Application of ', ['i', 'Three Rivers Imaging, LLC']],
      tribunalLine: 'DCH Commissioner · Final Decision',
      citations: ['CON No. 23-0118 (Final Order Aug. 7, 2024)'], docketNo: 'CON No. 23-0118', decided: 'August 7, 2024', subsequent: 'See Riverstone Imaging, 372 Ga. App. 488',
      treatment: { level: 'negative', word: 'Negative treatment.', glyph: '\u25CF', bg: '#8E1B1F', text: [' Methodology relied upon was reversed on judicial review in ', ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'], ', 372 Ga. App. 488 (2025).'] },
      editorial: 'Commissioner final order affirming the denial of a competing fixed-MRI application, applying the same five-county service-area methodology later reversed in Riverstone. Included here as the companion / competing-applicant docket.',
      headnotes: [
        { num: '1', key: 'CON III · 7', keyId: 'iii-7', topic: 'Need / Utilization', text: 'Applicant failed to rebut the Department\u2019s MRI need methodology under Rule 111-2-2-.40 for the Bartow County primary service area; absent a demonstration that the existing fixed unit is at or above threshold utilization, no unmet need was shown. (Methodology subsequently reversed in Riverstone.)' },
      ],
      byline: 'MURRAY, Commissioner.',
      intro: 'This matter comes before the Commissioner on review of the Hearing Officer\u2019s initial decision. Having reviewed the record, the initial decision is adopted in full.',
      paragraphs: [
        { num: '1', segs: ['Three Rivers Imaging applied under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' for a fixed MRI unit serving Bartow County, as a competing applicant to ', ['case', 'Riverstone Imaging', 'riverstone-imaging'], '.'] },
        { num: '2', segs: ['Applying the five-county service-area methodology under ', ['stat', 'Rule 111-2-2-.40', 'rule-111-2-2-.40'], ', the Department found the existing fixed unit below the utilization threshold and denied both applications.'] },
        { num: '3', segs: ['The Hearing Officer affirmed, and the Commissioner adopts that decision. ', ['i', 'Note: the service-area methodology applied here was subsequently held unsupported by substantial evidence in '], ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'], '.'] },
      ],
      disposition: [['b', 'Initial decision adopted; application denied.']],
      meta: { Service: 'Fixed MRI (1.5T)', Applicant: 'Three Rivers Imaging, LLC', County: 'Bartow County', 'CON No.': '23-0118', Status: 'Competing applicant', Decided: 'Aug. 7, 2024' },
      counsel: [
        { role: 'For Applicant Three Rivers', name: 'Stephen P. Maddox', firm: 'Maddox & Wexler' },
        { role: 'For the Department', name: 'Carrie A. Hanlon', firm: 'Senior Assistant A.G.' },
      ],
      docketDays: '524 days', docketDispositions: 4,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed (competing)', cite: 'CON 23-0118', date: 'Mar. 3, 2023', outcome: 'Filed', oc: 'gray', marker: 'open', summary: 'Competing fixed-MRI application, Bartow County.', filingsCount: 9, judge: 'M. Patel' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Denied', cite: 'DCH Init. Dec. (2023)', date: 'Jun. 30, 2023', outcome: 'Denied', oc: 'red', marker: 'red', summary: 'Denied under five-county methodology.', filingsCount: 3, judge: 'M. Patel', duration: '119 days', hasOpinion: true }),
        stage({ stageNum: '03', stageLabel: 'Hearing', court: 'OSAH', title: 'Initial Decision — Affirmed', cite: 'OSAH-DCH-CON-23-118', date: 'Feb. 14, 2024', outcome: 'Affirmed', oc: 'gray', marker: 'gray', summary: 'Consolidated hearing with Riverstone.', filingsCount: 22, judge: 'Walsh, ALJ', duration: '229 days', hasOpinion: true }),
        stage({ stageNum: '04', stageLabel: 'Final Decision', court: 'DCH Commissioner', title: 'Final Order — Affirmed Denial', cite: 'DCH Final Order (Aug. 7, 2024)', date: 'Aug. 7, 2024', outcome: 'Affirmed', oc: 'red', marker: 'red', summary: 'Commissioner adopted initial decision. Methodology later reversed in Riverstone.', filingsCount: 4, judge: 'Murray, Comm\u2019r', duration: '175 days', isCurrent: true, hasOpinion: true, opinionSelf: true, last: true }),
      ],
      chrono: [
        ['07', 'Aug', '2024', 'Order · DCH', 'red', 'FINAL ORDER — Affirmed Denial', 'Comm\u2019r Murray'],
        ['14', 'Feb', '2024', 'Order · OSAH', 'gray', 'INITIAL DECISION — Affirmed', 'Walsh, ALJ'],
        ['30', 'Jun', '2023', 'Order · DCH', 'red', 'INITIAL DECISION — Denied', 'M. Patel'],
        ['03', 'Mar', '2023', 'Filing', 'gray', 'CON Application filed', 'Three Rivers Imaging, LLC'],
      ],
      briefs: [
        { title: 'Applicant\u2019s Post-Hearing Brief', meta: 'Stephen P. Maddox, Maddox & Wexler · 29 pp.' },
      ],
      citator: {
        flags: [ { label: 'Citing', count: 9, color: '#141414' }, { label: 'Positive', count: 3, color: '#10B981' }, { label: 'Cautionary', count: 2, color: '#F59E0B' }, { label: 'Negative', count: 4, color: '#8E1B1F' } ],
        cases: [
          { badge: 'CON', dktNum: '372 Ga. App. 488', treat: 'Reversed (methodology)', level: 'negative', title: 'Riverstone Imaging, LLC v. DCH', cite: '372 Ga. App. 488 (2025)', depth: 4, snippet: 'The five-county service-area methodology applied in this companion docket was held unsupported by substantial evidence.', keys: [['CON III·7', 'iii-7']], target: 'riverstone-imaging' },
        ],
        toa: [
          { title: 'O.C.G.A. § 31-6-43 — Granting or Denying CON', cite: 'Ga. Code Ann.', pinpoint: 'subsection (a)', target: '31-6-43', kind: 'stat' },
          { title: 'Ga. Comp. R. & Regs. 111-2-2-.40', cite: 'Ga. Comp. R. & Regs.', pinpoint: '(4)(b)', target: 'rule-111-2-2-.40', kind: 'stat' },
        ],
      },
    },

    // ---------- NORTHRIDGE ----------
    'northridge': {
      id: 'northridge', badge: 'CON', dktNum: 'CON 2025028',
      captionParts: ['In re ', ['i', 'Northridge Cardiac Services, LLC'], ' — CON No. 24-0042'],
      tribunalLine: 'DCH Planning Section · Initial Decision',
      citations: ['DCH Init. Dec. Nov. 1, 2024'], docketNo: 'CON No. 24-0042', decided: 'November 1, 2024', subsequent: 'No subsequent history',
      treatment: { level: 'neutral', word: 'No subsequent history.', glyph: '\u25CF', bg: '#8A8472', text: [' Initial decision; no administrative or judicial review of record.'] },
      editorial: 'Initial decision denying a CON for a cardiac catheterization lab. Held: the five-year projected procedure volume fell below the minimum threshold of Rule 111-2-2-.22(4)(c).',
      headnotes: [
        { num: '1', key: 'CON IV · 15', keyId: 'iv-15', topic: 'Cardiac Cath / OHS — Need', text: 'A proposed cardiac catheterization service does not meet the need methodology threshold of Rule 111-2-2-.22(4)(c) where the five-year projected procedure volume falls below the minimum required volume.' },
      ],
      byline: 'GOODMAN, Planning Officer.',
      intro: 'This is the initial decision of the Department on the application of Northridge Cardiac Services, LLC, for a certificate of need to establish a cardiac catheterization service in Forsyth County.',
      paragraphs: [
        { num: '1', segs: ['Northridge applied under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' for a cardiac catheterization laboratory in Forsyth County.'] },
        { num: '2', segs: ['Under ', ['stat', 'Rule 111-2-2-.22(4)(c)', 'rule-111-2-2-.22'], ', an application must project a minimum of 750 procedures within five years. Applicant\u2019s projection of 612 cases falls below this threshold.'] },
        { num: '3', segs: ['Accordingly, the application is denied for failure to demonstrate need.'] },
      ],
      disposition: [['b', 'Application denied.']],
      meta: { Service: 'Cardiac Catheterization', Applicant: 'Northridge Cardiac Services, LLC', County: 'Forsyth', 'CON No.': '24-0042', Decided: 'Nov. 1, 2024' },
      counsel: [ { role: 'For Applicant Northridge', name: 'J. Goodman', firm: 'In-house counsel' } ],
      docketDays: '142 days', docketDispositions: 2,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed', cite: 'CON 2025028', date: 'Jun. 12, 2025', outcome: 'Filed', oc: 'gray', marker: 'open', summary: 'Cardiac catheterization lab, Forsyth County.', filingsCount: 8, judge: 'J. Goodman' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Denied', cite: 'DCH Init. Dec. (Nov. 1, 2024)', date: 'Nov. 1, 2024', outcome: 'Denied', oc: 'red', marker: 'red', summary: 'Projected 612 cases below 750-procedure threshold of Rule 111-2-2-.22(4)(c).', filingsCount: 3, judge: 'J. Goodman', duration: '142 days', isCurrent: true, hasOpinion: true, opinionSelf: true, last: true }),
      ],
      chrono: [
        ['01', 'Nov', '2024', 'Order · DCH', 'red', 'INITIAL DECISION — Denied', 'J. Goodman'],
        ['12', 'Jun', '2025', 'Filing', 'gray', 'CON Application filed', 'Northridge Cardiac Services, LLC'],
      ],
      briefs: [],
      citator: {
        flags: [ { label: 'Citing', count: 2, color: '#141414' }, { label: 'Positive', count: 1, color: '#10B981' }, { label: 'Cautionary', count: 0, color: '#F59E0B' }, { label: 'Negative', count: 0, color: '#8E1B1F' } ],
        cases: [],
        toa: [
          { title: 'Ga. Comp. R. & Regs. 111-2-2-.22 — Cardiac Catheterization', cite: 'Ga. Comp. R. & Regs.', pinpoint: '(4)(c)', target: 'rule-111-2-2-.22', kind: 'stat' },
          { title: 'O.C.G.A. § 31-6-43', cite: 'Ga. Code Ann.', pinpoint: 'subsection (a)', target: '31-6-43', kind: 'stat' },
        ],
      },
    },

    // ---------- COBBLESTONE ----------
    'cobblestone': {
      id: 'cobblestone', badge: 'CON', dktNum: 'CON 2025017',
      captionParts: [['i', 'Cobblestone Surgical Partners, LLC'], ' v. ', ['i', 'Georgia Department of Community Health']],
      tribunalLine: 'Office of State Administrative Hearings · Initial Decision',
      citations: ['OSAH-DCH-CON-25-018-Kennedy'], docketNo: 'OSAH-DCH-CON-25-018', decided: 'February 14, 2025', subsequent: 'Adopted by Commissioner, Nov. 19, 2025',
      treatment: { level: 'positive', word: 'Positive.', glyph: '\u2713', bg: '#10B981', text: [' Recommended grant adopted by Commissioner; no negative history.'] },
      editorial: 'Hearing Officer recommended grant of a CON for a multispecialty ASC, holding that the Department\u2019s rigid single-county service area, divorced from referral and physician-practice patterns, is inconsistent with the substantial-evidence standard of Coastal Empire.',
      headnotes: [
        { num: '1', key: 'CON IV · 13', keyId: 'iv-13', topic: 'Ambulatory Surgery (ASC) — Need', text: 'The Department\u2019s rigid application of a single-county service area, divorced from referral patterns and physician practice patterns, is inconsistent with the substantial-evidence standard articulated in Coastal Empire.' },
        { num: '2', key: 'CON V · 21', keyId: 'v-21', topic: 'Burden of Proof', text: 'On administrative review, the applicant bears the burden of demonstrating need; that burden is met where referral and physician-practice data establish a multi-county draw inconsistent with the Department\u2019s single-county definition.' },
      ],
      byline: 'KENNEDY, Administrative Law Judge.',
      intro: 'This matter comes before the Office of State Administrative Hearings on the request of Cobblestone Surgical Partners, LLC, for review of the Department\u2019s denial of a CON for a multispecialty ambulatory surgery center in Chatham County.',
      paragraphs: [
        { num: '1', segs: ['Cobblestone applied under ', ['stat', 'O.C.G.A. § 31-6-43', '31-6-43'], ' for a multispecialty ASC in Chatham County. The Department denied the application on a single-county service-area analysis.'] },
        { num: '2', segs: ['The Department\u2019s rigid application of a single-county service area, divorced from referral patterns and physician practice patterns, is inconsistent with the substantial-evidence standard articulated in ', ['case', 'Coastal Empire Hosp. Auth.', 'coastal-empire'], ', and the need methodology must account for the demonstrated travel patterns of the patient population.'] },
        { num: '3', segs: ['The record establishes a multi-county draw. Applicant has carried its burden under ', ['topic', 'CON V·21', 'v-21'], '. The undersigned recommends that the application be granted.'] },
      ],
      disposition: [['b', 'Recommended: grant of CON.'], ' ', ['i', 'Adopted by the Commissioner, Nov. 19, 2025.']],
      meta: { Service: 'Ambulatory Surgery (Multispecialty)', Applicant: 'Cobblestone Surgical Partners, LLC', County: 'Chatham', 'CON No.': '2025017', 'Hearing Officer': 'Kennedy, ALJ', Decided: 'Feb. 14, 2025' },
      counsel: [
        { role: 'For Applicant Cobblestone', name: 'Dana R. Whitfield', firm: 'Parker, Hudson, Rainer & Dobbs LLP' },
        { role: 'For the Department', name: 'Carrie A. Hanlon', firm: 'Senior Assistant A.G.' },
      ],
      docketDays: '420 days', docketDispositions: 4,
      flow: [
        stage({ stageNum: '01', stageLabel: 'Application', court: 'DCH Planning Section', title: 'CON Application Filed', cite: 'CON 2025017', date: 'Apr. 4, 2025', outcome: 'Filed', oc: 'gray', marker: 'open', summary: 'Multispecialty ASC, Chatham County.', filingsCount: 12, judge: 'M. Madison' }),
        stage({ stageNum: '02', stageLabel: 'Initial Decision', court: 'DCH Planning Section', title: 'Initial Decision — Denied', cite: 'DCH Init. Dec. (2025)', date: 'Jul. 18, 2025', outcome: 'Denied', oc: 'red', marker: 'red', summary: 'Denied on single-county service-area analysis.', filingsCount: 3, judge: 'M. Madison', duration: '105 days', hasOpinion: true }),
        stage({ stageNum: '03', stageLabel: 'Hearing', court: 'OSAH', title: 'Initial Decision — Recommended Grant', cite: 'OSAH-DCH-CON-25-018', date: 'Feb. 14, 2025', outcome: 'Granted', oc: 'green', marker: 'green', summary: 'Single-county service area divorced from referral patterns fails substantial-evidence standard. Recommends grant.', filingsCount: 24, judge: 'Kennedy, ALJ', duration: '211 days', isCurrent: true, hasOpinion: true, opinionSelf: true }),
        stage({ stageNum: '04', stageLabel: 'Final Decision', court: 'DCH Commissioner', title: 'Final Order — Adopted; CON Granted', cite: 'DCH Final Order (Nov. 19, 2025)', date: 'Nov. 19, 2025', outcome: 'Granted', oc: 'green', marker: 'green', summary: 'Commissioner adopted the Hearing Officer\u2019s recommendation in full.', filingsCount: 4, judge: 'Murray, Comm\u2019r', duration: '92 days', last: true }),
      ],
      chrono: [
        ['19', 'Nov', '2025', 'Order · DCH', 'green', 'FINAL ORDER — CON Granted', 'Comm\u2019r Murray'],
        ['14', 'Feb', '2025', 'Order · OSAH', 'green', 'INITIAL DECISION — Recommended Grant', 'Kennedy, ALJ'],
        ['18', 'Jul', '2025', 'Order · DCH', 'red', 'INITIAL DECISION — Denied', 'M. Madison'],
        ['04', 'Apr', '2025', 'Filing', 'gray', 'CON Application filed', 'Cobblestone Surgical Partners, LLC'],
      ],
      briefs: [
        { title: 'Applicant\u2019s Post-Hearing Brief', meta: 'Dana R. Whitfield, Parker, Hudson, Rainer & Dobbs LLP · 33 pp.' },
        { title: 'Department\u2019s Post-Hearing Brief', meta: 'Carrie A. Hanlon, Sr. Asst. A.G. · 27 pp.' },
      ],
      citator: {
        flags: [ { label: 'Citing', count: 4, color: '#141414' }, { label: 'Positive', count: 3, color: '#10B981' }, { label: 'Cautionary', count: 1, color: '#F59E0B' }, { label: 'Negative', count: 0, color: '#8E1B1F' } ],
        cases: [
          { badge: 'CON', dktNum: '—', treat: 'Followed', level: 'positive', title: 'In re Alliance Surgery Center', cite: 'DCH (2025)', depth: 2, snippet: 'Citing Cobblestone for the requirement to consider physician-practice patterns in ASC service-area analysis.', keys: [['CON IV·13', 'iv-13']], target: null },
        ],
        toa: [
          { title: 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC', cite: '358 Ga. App. 211 (2023)', pinpoint: 'pp. 215-217', target: 'coastal-empire', kind: 'case' },
          { title: 'O.C.G.A. § 31-6-43', cite: 'Ga. Code Ann.', pinpoint: 'subsection (a)', target: '31-6-43', kind: 'stat' },
        ],
      },
    },
  };

  window.CON_CORPUS = { cases: CASES, C: C };
})();
