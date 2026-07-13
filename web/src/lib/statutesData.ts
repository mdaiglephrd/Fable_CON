/*
 * Statutes & Rules fixture data — the comp's STATUTE_TOC / STATUTE_CONTENT /
 * RULES_CONTENT / RULE_LIST blocks, with the inline sLink/cLink cross-links
 * expressed in the corpus segment format (renderSegs handles routing).
 */
import type { Seg } from './types';

export interface StatuteTocEntry {
  num: string;
  id: string;
  title: string;
}

export const STATUTE_TOC: StatuteTocEntry[] = [
  { num: '§ 31-6-1', id: '31-6-1', title: 'Short title; legislative findings' },
  { num: '§ 31-6-2', id: '31-6-2', title: 'Definitions' },
  { num: '§ 31-6-21', id: '31-6-21', title: 'Authority of Department; rule-making' },
  { num: '§ 31-6-40', id: '31-6-40', title: 'New institutional health services requiring CON' },
  { num: '§ 31-6-42', id: '31-6-42', title: 'Considerations in reviewing applications' },
  { num: '§ 31-6-43', id: '31-6-43', title: 'Granting or denying CON; letter of determination' },
  { num: '§ 31-6-44', id: '31-6-44', title: 'Administrative appeals; hearing procedure' },
  { num: '§ 31-6-44.1', id: '31-6-44.1', title: 'Judicial review of final agency decision' },
  { num: '§ 31-6-45', id: '31-6-45', title: 'Capital expenditures; threshold' },
  { num: '§ 31-6-45.2', id: '31-6-45.2', title: 'Sanctions and penalties' },
];

export interface StatuteSubsection {
  num: string;
  segs: Seg[];
}

export interface StatuteContent {
  cite: string;
  title: string;
  subtitle: string;
  subs: StatuteSubsection[];
  history: string;
}

const SUBTITLE = 'Pt. of Ga. Code Ann., Tit. 31, Ch. 6 — State Health Planning';

export const STATUTE_CONTENT: Record<string, StatuteContent> = {
  '31-6-43': {
    cite: 'O.C.G.A. § 31-6-43',
    title: 'Granting or Denying Certificate of Need; Issuance of Letter of Determination',
    subtitle: SUBTITLE,
    subs: [
      {
        num: '(a)',
        segs: [
          'On a timely filed and complete application, the department shall, except as otherwise provided in this article, grant or deny each application for a certificate of need by the close of business on the 120th day following the day on which the application is deemed complete. The department shall apply the review considerations set forth in ',
          ['stat', '§ 31-6-42', '31-6-42'],
          ' and the service-specific need methodologies adopted under ',
          ['stat', 'Rule 111-2-2', 'rule-111-2-2-.09'],
          '. Failure of the department to act within 120 days shall not be deemed an approval of the application.',
        ],
      },
      {
        num: '(b)',
        segs: [
          'The department’s initial decision shall be set forth in a letter of determination stating, with particularity, the reasons for the action taken and the findings of fact and conclusions of law upon which the action rests. ',
          ['case', 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC', 'coastal-empire'],
          ', 358 Ga. App. 211 (2023) (letter of determination must articulate reasoned basis for departing from applicant’s service-area definition).',
        ],
      },
      {
        num: '(c)',
        segs: [
          'An applicant whose application has been denied, or any person who is aggrieved by the department’s decision and who has timely intervened pursuant to ',
          ['stat', '§ 31-6-44(a)', '31-6-44'],
          ', may request administrative review. A request for review must be filed with the department within thirty (30) days of the date the letter of determination is issued and shall comply with ',
          ['stat', 'Rule 111-2-2-.10', 'rule-111-2-2-.10'],
          '.',
        ],
      },
      {
        num: '(d)',
        segs: [
          'The department may condition the grant of a certificate of need upon (1) compliance with stated quality of care, indigent care, or charity care commitments; (2) achievement of stated utilization benchmarks within a specified period; and (3) such other conditions reasonably related to the considerations of ',
          ['stat', '§ 31-6-42', '31-6-42'],
          ' as the department may prescribe. Failure to satisfy conditions imposed under this subsection shall subject the certificate to revocation in accordance with ',
          ['stat', '§ 31-6-45.2', '31-6-45.2'],
          '.',
        ],
      },
      {
        num: '(e)',
        segs: [
          'The department shall, on the request of any person and within forty-five (45) days of receipt of a complete request, issue a letter of determination as to whether a proposed activity is a new institutional health service requiring a certificate of need under ',
          ['stat', '§ 31-6-40', '31-6-40'],
          '. A letter of determination issued under this subsection is a final agency action subject to judicial review under ',
          ['stat', '§ 31-6-44.1', '31-6-44.1'],
          '.',
        ],
      },
    ],
    history:
      'Code 1981, § 31-6-43, enacted by Ga. L. 1983, p. 1566, § 1; Ga. L. 1991, p. 1059, § 16; Ga. L. 2008, p. 12, § 1-1; Ga. L. 2019, p. 462, § 7/HB 186; Ga. L. 2024, p. 901, § 4/SB 418.',
  },
  '31-6-44': {
    cite: 'O.C.G.A. § 31-6-44',
    title: 'Administrative Appeals; Hearing Procedure',
    subtitle: SUBTITLE,
    subs: [
      {
        num: '(a)',
        segs: [
          'Any person considered by the department in connection with an application, and any competing applicant, may seek review of the department’s initial decision by filing a request for an administrative hearing within 30 days. Intervention is governed by ',
          ['stat', 'Rule 111-2-2-.10', 'rule-111-2-2-.10'],
          '.',
        ],
      },
      {
        num: '(b)',
        segs: [
          'The hearing shall be conducted before a hearing officer of the Office of State Administrative Hearings in accordance with Chapter 13 of Title 50. The hearing officer shall issue an initial decision containing findings of fact and conclusions of law.',
        ],
      },
      {
        num: '(c)',
        segs: [
          'Within 30 days of the hearing officer’s initial decision, any party may request review by the commissioner, whose decision constitutes the final decision of the department for purposes of ',
          ['stat', '§ 31-6-44.1', '31-6-44.1'],
          '. ',
          ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'],
          ', 372 Ga. App. 488 (2025).',
        ],
      },
    ],
    history:
      'Code 1981, § 31-6-44, enacted by Ga. L. 1983, p. 1566, § 1; Ga. L. 2008, p. 12, § 1-1; Ga. L. 2019, p. 462, § 8/HB 186.',
  },
  '31-6-44.1': {
    cite: 'O.C.G.A. § 31-6-44.1',
    title: 'Judicial Review of Final Agency Decision',
    subtitle: SUBTITLE,
    subs: [
      {
        num: '(a)',
        segs: [
          'Any party to the initial administrative hearing who is aggrieved by a final decision of the department is entitled to judicial review in the superior court of the county in which the proposed project is to be located. The petition shall be filed within 30 days of the final decision.',
        ],
      },
      {
        num: '(b)',
        segs: [
          'Judicial review shall be conducted by the court without a jury and is confined to the record. The court shall not substitute its judgment for that of the department as to the weight of the evidence on questions of fact. The court may reverse or modify the decision if substantial rights of the petitioner have been prejudiced because the findings are clearly erroneous or unsupported by ',
          ['case', 'substantial evidence', 'riverstone-imaging'],
          ' in view of the reliable, probative, and substantial evidence on the whole record.',
        ],
      },
      {
        num: '(c)',
        segs: [
          'An aggrieved party may appeal the decision of the superior court to the Court of Appeals or the Supreme Court of Georgia in accordance with the appellate practice statutes.',
        ],
      },
    ],
    history:
      'Code 1981, § 31-6-44.1, enacted by Ga. L. 2008, p. 12, § 1-1; Ga. L. 2019, p. 462, § 9/HB 186.',
  },
  '31-6-42': {
    cite: 'O.C.G.A. § 31-6-42',
    title: 'Considerations in Reviewing Applications',
    subtitle: SUBTITLE,
    subs: [
      {
        num: '(a)',
        segs: [
          'In determining whether to grant a certificate of need, the department shall apply the considerations set forth in this Code section and the rules adopted pursuant to ',
          ['stat', '§ 31-6-21', '31-6-21'],
          ', including: (1) the need of the population for the proposed service; (2) the availability of less costly or more effective alternatives; (3) the financial feasibility of the proposal; (4) the relationship of the proposal to the existing health care delivery system; and (5) the extent to which the proposal will serve medically underserved populations.',
        ],
      },
      {
        num: '(b)',
        segs: [
          'The service-specific need methodologies adopted under ',
          ['stat', 'Rule 111-2-2', 'rule-111-2-2-.09'],
          ' shall govern the quantitative need determination for each category of new institutional health service.',
        ],
      },
    ],
    history:
      'Code 1981, § 31-6-42, enacted by Ga. L. 1983, p. 1566, § 1; Ga. L. 2008, p. 12, § 1-1.',
  },
  '31-6-40': {
    cite: 'O.C.G.A. § 31-6-40',
    title: 'New Institutional Health Services Requiring a Certificate of Need',
    subtitle: SUBTITLE,
    subs: [
      {
        num: '(a)',
        segs: [
          'On and after the effective date of this chapter, any new institutional health service shall be required to obtain a certificate of need pursuant to this chapter. “New institutional health service” includes the construction or establishment of a new health care facility; any expenditure exceeding the capital expenditure threshold of ',
          ['stat', '§ 31-6-45', '31-6-45'],
          '; and the offering of a new clinical health service.',
        ],
      },
      {
        num: '(b)',
        segs: [
          'The acquisition of major medical equipment, and the establishment of a diagnostic, treatment, or rehabilitation center, are subject to review as provided in ',
          ['stat', 'Rule 111-2-2', 'rule-111-2-2-.09'],
          '.',
        ],
      },
    ],
    history:
      'Code 1981, § 31-6-40, enacted by Ga. L. 1983, p. 1566, § 1; Ga. L. 2008, p. 12, § 1-1; Ga. L. 2019, p. 462, § 6/HB 186.',
  },
};

export const FALLBACK_SUBS: StatuteSubsection[] = [
  {
    num: '(a)',
    segs: [
      'The full annotated text of this provision is available in the corpus. This section is part of Georgia’s Certificate of Need program under O.C.G.A. § 31-6-1 ',
      ['i', 'et seq.'],
      ' and is implemented through ',
      ['stat', 'Ga. Comp. R. & Regs. 111-2-2', 'rule-111-2-2-.09'],
      '.',
    ],
  },
];

export function statuteContentFor(statuteId: string): StatuteContent {
  const curated = STATUTE_CONTENT[statuteId];
  if (curated) return curated;
  const toc = STATUTE_TOC.find((s) => s.id === statuteId);
  return {
    cite: toc ? `O.C.G.A. ${toc.num}` : 'O.C.G.A. § 31-6',
    title: toc ? toc.title : 'Georgia Certificate of Need',
    subtitle: SUBTITLE,
    subs: FALLBACK_SUBS,
    history: 'Code 1981, enacted by Ga. L. 1983, p. 1566, § 1; subsequently amended.',
  };
}

// ---------------------------------------------------------------------------
// DCH rules (Ga. Comp. R. & Regs. 111-2-2)
// ---------------------------------------------------------------------------

export interface RuleContent {
  title: string;
  subs: StatuteSubsection[];
  authority: string;
}

export const RULES_CONTENT: Record<string, RuleContent> = {
  'rule-111-2-2-.40': {
    title: 'Rule 111-2-2-.40 — MRI Need Methodology',
    subs: [
      {
        num: '(1)',
        segs: [
          'Purpose. This rule establishes the methodology used by the Department to determine the need for fixed and mobile magnetic resonance imaging (MRI) services in Georgia. This methodology shall be applied to all applications for certificates of need involving MRI equipment submitted under ',
          ['stat', '§ 31-6-43', '31-6-43'],
          '.',
        ],
      },
      {
        num: '(2)',
        segs: [
          'Definitions. As used in this rule: (a) "Fixed MRI" means a 1.0 Tesla or higher MRI unit installed in a permanent location. (b) "Mobile MRI" means an MRI unit mounted in a vehicle or transported between locations. (c) "Primary service area" or "PSA" means the geographic area from which an applicant projects 75% or more of its MRI procedures.',
        ],
      },
      {
        num: '(3)',
        segs: [
          'Service area. The Department shall use the applicant’s demonstrated referral patterns and geographic contiguity as the primary bases for defining the PSA. The Department shall not define the PSA solely on geographic contiguity absent record evidence supporting that definition. ',
          ['i', 'See '],
          ['stat', '§ 31-6-43(b)', '31-6-43'],
          '; ',
          ['case', 'Riverstone Imaging, LLC v. DCH', 'riverstone-imaging'],
          ', 372 Ga. App. 488 (2025).',
        ],
      },
      {
        num: '(4)(b)',
        segs: [
          'Fixed MRI threshold. An application to establish a fixed MRI service shall not be approved unless the existing fixed MRI unit(s) within the PSA are operating at or above 6,000 procedures per year on a rolling 12-month basis. Where an existing unit is operating below this threshold, the applicant bears the burden of demonstrating why additional capacity is nonetheless needed.',
        ],
      },
      {
        num: '(5)',
        segs: [
          'Mobile MRI. An application to establish a mobile MRI service shall demonstrate that the proposed mobile unit will serve a minimum of 1,800 procedures per year by the end of its second year of operation, based on documented contractual commitments from referring physicians.',
        ],
      },
    ],
    authority:
      'O.C.G.A. § 31-6-21; Ga. L. 1983, p. 1566; amended effective Jan. 1, 2020; proposed amendments pending (comment period open through Jul. 15, 2026).',
  },
  'rule-111-2-2-.09': {
    title: 'Rule 111-2-2-.09 — Review Considerations',
    subs: [
      {
        num: '(1)',
        segs: [
          'General. In reviewing any application for a certificate of need, the Department shall consider the criteria set forth in ',
          ['stat', '§ 31-6-42', '31-6-42'],
          ', weighted against the costs and benefits of the proposed project to the populations of the service area.',
        ],
      },
      {
        num: '(2)',
        segs: [
          'Need. The Department shall apply the service-specific need methodology applicable to the category of service proposed, as set forth in the applicable service-specific rule.',
        ],
      },
      {
        num: '(3)',
        segs: [
          'Financial feasibility. The applicant shall demonstrate, through a projected three-year pro forma income statement and balance sheet, that the proposed service is financially feasible on a stand-alone basis. The projections shall be supported by documented assumptions.',
        ],
      },
    ],
    authority: 'O.C.G.A. §§ 31-6-21, 31-6-42; Ga. L. 1983, p. 1566.',
  },
  'rule-111-2-2-.10': {
    title: 'Rule 111-2-2-.10 — Administrative Hearing Procedures',
    subs: [
      {
        num: '(1)',
        segs: [
          'Applicability. This rule governs requests for administrative hearings filed under ',
          ['stat', '§ 31-6-44', '31-6-44'],
          ' and proceedings conducted before the Office of State Administrative Hearings (OSAH).',
        ],
      },
      {
        num: '(2)',
        segs: [
          'Standing to request hearing. An applicant whose application has been denied, a competing applicant in the same batching cycle, or any person who has timely intervened pursuant to subsection (3) of this rule, may request a hearing within 30 days of the letter of determination.',
        ],
      },
      {
        num: '(3)',
        segs: [
          'Intervention. Any person who may be substantially affected by the grant or denial of an application may petition to intervene. The petition must be filed within 20 days of the date the application is deemed complete and must demonstrate a direct and substantial interest in the outcome distinct from that of the general public.',
        ],
      },
    ],
    authority: 'O.C.G.A. §§ 31-6-21, 31-6-44; O.C.G.A. § 50-13-17 (APA).',
  },
};

export const DEFAULT_RULE: RuleContent = {
  title: 'Ga. Comp. R. & Regs. 111-2-2 — Certificate of Need Rules',
  subs: [
    {
      num: '(General)',
      segs: [
        'Select a rule section from the table of contents. This chapter implements the Georgia Certificate of Need program under ',
        ['stat', '§ 31-6-1', '31-6-1'],
        ' ',
        ['i', 'et seq.'],
      ],
    },
  ],
  authority: 'O.C.G.A. § 31-6-21.',
};

export const RULES_TOC: { id: string; label: string; title: string }[] = [
  { id: 'rule-111-2-2-.01', label: '111-2-2-.01', title: 'General Provisions' },
  { id: 'rule-111-2-2-.09', label: '111-2-2-.09', title: 'Review Considerations' },
  { id: 'rule-111-2-2-.10', label: '111-2-2-.10', title: 'Administrative Hearing Procedures' },
  { id: 'rule-111-2-2-.22', label: '111-2-2-.22', title: 'Cardiac Catheterization' },
  { id: 'rule-111-2-2-.26', label: '111-2-2-.26', title: 'Long-Term Care' },
  { id: 'rule-111-2-2-.40', label: '111-2-2-.40', title: 'MRI Need Methodology' },
];

/** The Statutes & Rules index — DCH rule chapter listing (comp's RULE_LIST). */
export const RULE_LIST: { num: string; id: string; title: string }[] = [
  { num: '111-2-2-.09', id: 'rule-111-2-2-.09', title: 'General review considerations and procedures' },
  { num: '111-2-2-.10', id: 'rule-111-2-2-.10', title: 'Administrative appeal procedures' },
  { num: '111-2-2-.20', id: 'rule-111-2-2-.20', title: 'Hospital beds — need methodology' },
  { num: '111-2-2-.22', id: 'rule-111-2-2-.22', title: 'Cardiac catheterization services' },
  { num: '111-2-2-.24', id: 'rule-111-2-2-.24', title: 'Open heart surgery services' },
  { num: '111-2-2-.31', id: 'rule-111-2-2-.31', title: 'Radiation therapy services' },
  { num: '111-2-2-.40', id: 'rule-111-2-2-.40', title: 'Magnetic resonance imaging (MRI)' },
  { num: '111-2-2-.41', id: 'rule-111-2-2-.41', title: 'Positron emission tomography (PET)' },
  { num: '111-2-2-.50', id: 'rule-111-2-2-.50', title: 'Ambulatory surgery centers' },
];

export function ruleContentFor(ruleId: string): RuleContent {
  const curated = RULES_CONTENT[ruleId];
  if (curated) return curated;
  const toc = RULES_TOC.find((r) => r.id === ruleId) || RULE_LIST.find((r) => r.id === ruleId);
  if (!toc) return DEFAULT_RULE;
  return {
    ...DEFAULT_RULE,
    title: `Rule ${'label' in toc ? toc.label : toc.num} — ${toc.title}`,
  };
}

// ---------------------------------------------------------------------------
// Annotations rail (citing cases, comp's statuteAnnotations)
// ---------------------------------------------------------------------------

export interface StatuteAnnotation {
  subsection: string;
  label: string;
  borderColor: string;
  title: string;
  cite: string;
  holding: string;
  caseId: string | null;
}

export const STATUTE_ANNOTATIONS: StatuteAnnotation[] = [
  {
    subsection: '(a)',
    label: '120-Day Period',
    borderColor: 'var(--text3)',
    title: 'In re Bartow County ASC',
    cite: 'CON 23-0224 (DCH 2024)',
    holding:
      'Failure of department to act within 120-day period does not result in deemed approval; statute is directive, not jurisdictional.',
    caseId: null,
  },
  {
    subsection: '(b)',
    label: 'Findings of Fact',
    borderColor: '#10B981',
    title: 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC',
    cite: '358 Ga. App. 211 (2023)',
    holding:
      'Letter of determination must articulate reasoned basis for departing from applicant’s service-area definition; bare invocation of geographic contiguity is insufficient.',
    caseId: 'coastal-empire',
  },
  {
    subsection: '(b)',
    label: 'Service Area',
    borderColor: '#F59E0B',
    title: 'Riverstone Imaging, LLC v. DCH',
    cite: '372 Ga. App. 488 (2025)',
    holding:
      'Service-area methodology that disregards record evidence of referral patterns fails substantial-evidence test.',
    caseId: 'riverstone-imaging',
  },
  {
    subsection: '(c)',
    label: '30-Day Window',
    borderColor: 'var(--accent-text)',
    title: 'In re Brookhaven Surgical Ctr.',
    cite: 'CON 22-0091 (OSAH 2023)',
    holding:
      'Request for administrative review filed on day 31 is untimely; statutory 30-day period under § 31-6-43(c) is jurisdictional.',
    caseId: null,
  },
  {
    subsection: '(d)',
    label: 'Conditions on Grant',
    borderColor: 'var(--text3)',
    title: 'In re Northridge Cardiac Servs., LLC',
    cite: 'DCH 24-0042 (2024)',
    holding:
      'Indigent-care condition imposed at 4.5% of gross revenues survives challenge as reasonably related to § 31-6-42 considerations.',
    caseId: 'northridge',
  },
];
