/*
 * Dev-fixture data layer — serves the con-corpus sample data so the console
 * runs standalone (VITE_USE_FIXTURES=true, the default in dev).
 *
 * corpus.json is generated from tests/fixtures/handoff/con-corpus.js by
 * web/scripts/generate-corpus.mjs (committed; re-run on corpus changes).
 * The docket roll (RECENT_DOCKETS) and result-card copy mirror the design
 * comp georgia-con-research.dc.html.
 */
import corpusJson from './corpus.json';
import {
  build,
  RIVERSTONE_CON,
  type DocketRecord,
  type Proceeding,
} from './docketEngine';
import type {
  CaseReader,
  CitatorReport,
  ResultCard,
  Seg,
} from './types';

// ---------------------------------------------------------------------------
// Corpus
// ---------------------------------------------------------------------------

interface CorpusShape {
  cases: Record<string, CaseReader>;
  C: Record<string, string>;
}

export const CORPUS = corpusJson as unknown as CorpusShape;
export const CASES = CORPUS.cases;

export function fixtureGetCase(id: string): CaseReader | null {
  const rec = CASES[id];
  if (!rec) return null;
  return { ...rec, entryId: id, docketId: CASE_TO_NUM[id] ?? null };
}

export function fixtureGetCitator(id: string): CitatorReport | null {
  const rec = CASES[id];
  if (!rec || !rec.citator) return null;
  return {
    entryId: id,
    flags: rec.citator.flags ?? [],
    citingCases: rec.citator.cases ?? [],
    tableOfAuthorities: rec.citator.toa ?? [],
  };
}

// ---------------------------------------------------------------------------
// Docket type registry + sample docket roll (from the design comp)
// ---------------------------------------------------------------------------

export interface DocketTypeMeta {
  label: string;
  full: string;
  fill: string;
}

export const DOCKET_TYPES: Record<string, DocketTypeMeta> = {
  CON: { label: 'CON', full: 'Certificate of Need Application', fill: '#8E1B1F' },
  DET: { label: 'DET', full: 'Determination of Reviewability', fill: '#F59E0B' },
  'DET-ASC': { label: 'DET·ASC', full: 'DOR — Ambulatory Surgery Center', fill: '#10B981' },
  'DET-EQT': { label: 'DET·EQT', full: 'DOR — Equipment', fill: '#8B5CF6' },
  'LNR-ASC': { label: 'LNR·ASC', full: 'Letter of Nonreviewability — ASC', fill: '#3B82F6' },
  'LNR-EQT': { label: 'LNR·EQT', full: 'Letter of Nonreviewability — Equip.', fill: '#8B5CF6' },
};

/** Sample of recent dockets drawn from the published DCH project lists. */
export const RECENT_DOCKETS: DocketRecord[] = [
  { type: 'DET-EQT', num: 'DET-EQT2026062', facility: "Emory Saint Joseph's Hospital", title: 'Replacement of da Vinci Robot', received: '4/22/2026', date: null, finding: 'Pending', county: 'Fulton', contact: 'J. Goodman' },
  { type: 'DET-EQT', num: 'DET-EQT2026061', facility: 'Piedmont Mountainside Hospital', title: 'Replace / Repair Single-Plane Vascular X-Ray System', received: '4/14/2026', date: null, finding: 'Pending', county: 'Pickens', contact: 'C. MacEwen' },
  { type: 'DET-EQT', num: 'DET-EQT2026060', facility: 'Piedmont Henry Hospital', title: 'Acquisition of Mobile MRI', received: '4/14/2026', date: null, finding: 'Pending', county: 'Henry', contact: 'C. MacEwen' },
  { type: 'DET-EQT', num: 'DET-EQT2026059', facility: 'Emory Hospital Warner Robins (Houston Hosps.)', title: 'EHWR MRI and CT Acquisition', received: '4/13/2026', date: null, finding: 'Pending', county: 'Houston', contact: 'M. Phagan' },
  { type: 'DET-EQT', num: 'DET-EQT2026058', facility: 'Union General Hospital', title: 'Acquisition of Fixed PET/CT', received: '3/16/2026', date: null, finding: 'Pending', county: 'Union', contact: 'M. Madison' },
  { type: 'DET-EQT', num: 'DET-EQT2026057', facility: "Emory Saint Joseph's Hospital", title: 'ESJH MRI at Vinings', received: '3/16/2026', date: null, finding: 'Pending', county: 'Cobb', contact: 'J. Goodman' },
  { type: 'DET-EQT', num: 'DET-EQT2026055', facility: 'Piedmont Hospital, Inc.', title: 'Linear Accelerator', received: '3/13/2026', date: null, finding: 'Pending', county: 'Fulton', contact: 'C. Macewen' },
  { type: 'DET-EQT', num: 'DET-EQT2026053', facility: 'Piedmont Columbus Regional Midtown', title: 'Acquisition of Cardiac Catheterization Equipment', received: '3/13/2026', date: null, finding: 'Pending', county: 'Muscogee', contact: 'C. MacEwen' },
  { type: 'DET-EQT', num: 'DET-EQT2026051', facility: 'AIENT Management Company LLC', title: 'CT Scanner Request', received: '3/4/2026', date: null, finding: 'Withdrawn', county: 'Fulton', contact: 'R. Sinha' },
  { type: 'DET-EQT', num: 'DET-EQT2026050', facility: 'Tift Regional Health System, Inc.', title: 'Acquisition of Philips Azurion 7M20', received: '2/27/2026', date: null, finding: 'Pending', county: 'Tift', contact: 'T. Branch' },
  { type: 'DET-EQT', num: 'DET-EQT2026049', facility: 'Atrium Health Navicent', title: 'Acquisition of a Nuclear Medicine Camera', received: '2/26/2026', date: null, finding: 'Pending', county: 'Bibb', contact: 'B. Dennie' },
  { type: 'DET-EQT', num: 'DET-EQT2026047', facility: "St. Mary's Good Samaritan Hospital", title: 'Good Samaritan Mobile PET/CT', received: '2/25/2026', date: null, finding: 'Pending', county: 'Greene', contact: 'J. Herring' },
  { type: 'DET-EQT', num: 'DET-EQT2026046', facility: "St. Mary's Sacred Heart Hospital", title: 'Sacred Heart Mobile PET/CT', received: '2/25/2026', date: null, finding: 'Pending', county: 'Franklin', contact: 'J. Herring' },
  { type: 'DET', num: 'DET2026006', facility: 'Piedmont Healthcare / Encompass Health', title: 'Joint Venture — Acute Rehab Hospital', received: '3/28/2026', date: null, finding: 'Pending', county: 'Forsyth', contact: 'C. MacEwen' },
  { type: 'DET', num: 'DET2026005', facility: 'Emory University Hospital', title: 'Bed Reconfiguration — Neuro ICU', received: '3/14/2026', date: null, finding: 'Pending', county: 'DeKalb', contact: 'J. Goodman' },
  { type: 'DET', num: 'DET2026004', facility: 'Wellstar Douglas Hospital', title: 'Replacement of Cath Lab Suite', received: '2/28/2026', date: '4/4/2026', finding: 'Approved', county: 'Douglas', contact: 'K. Andrews' },
  { type: 'DET', num: 'DET2026003', facility: 'Northside Hospital, Inc.', title: 'Conversion of Skilled Nursing Beds', received: '2/14/2026', date: '4/11/2026', finding: 'Approved', county: 'Fulton', contact: 'M. Madison' },
  { type: 'DET', num: 'DET2026001', facility: 'East Georgia Regional Medical Center', title: 'Renovation / Replacement of Inpatient Tower', received: '1/22/2026', date: '3/28/2026', finding: 'Approved', county: 'Bulloch', contact: 'T. Branch' },
  { type: 'CON', num: '2026007', facility: 'Riverstone Imaging, LLC', title: 'Fixed 1.5T MRI — Bartow County (on remand)', received: '4/8/2026', date: null, finding: 'Pending', county: 'Bartow', contact: 'A. Halverson' },
  { type: 'CON', num: '2026004', facility: 'Magnolia Behavioral Health, LLC', title: 'Psychiatric Beds — 48, Fulton/DeKalb PSA', received: '2/4/2026', date: '4/14/2026', finding: 'Denied', county: 'DeKalb', contact: 'C. MacEwen' },
  { type: 'CON', num: '2026002', facility: 'Three Rivers Imaging, LLC', title: 'Fixed MRI — Bartow County', received: '1/8/2026', date: '4/2/2026', finding: 'Approved', county: 'Bartow', contact: 'S. Maddox' },
  { type: 'CON', num: '2025028', facility: 'Northridge Cardiac Servs., LLC', title: 'Cardiac Catheterization Lab — Forsyth Co.', received: '6/12/2025', date: '11/1/2025', finding: 'Denied', county: 'Forsyth', contact: 'J. Goodman' },
  { type: 'CON', num: '2025017', facility: 'Cobblestone Surgical Partners, LLC', title: 'Multispecialty ASC — Chatham County', received: '4/4/2025', date: '11/19/2025', finding: 'Approved', county: 'Chatham', contact: 'M. Madison' },
  { type: 'DET-ASC', num: 'DET-ASC2025007', facility: 'Hughston Surgical Center of Valdosta, LLC', title: 'Physician-Owned Multispecialty ASC', received: '8/14/2025', date: '11/10/2025', finding: 'Approved', county: 'Lowndes', contact: 'C. MacEwen' },
  { type: 'DET-ASC', num: 'DET-ASC2025004', facility: 'Alliance Surgery Center at Peachtree City', title: 'Joint Venture, Single Specialty ASC', received: '5/2/2025', date: '8/14/2025', finding: 'Approved', county: 'Fayette', contact: 'J. Atkins' },
  { type: 'DET-ASC', num: 'DET-ASC2024012', facility: 'Southeast Eye Laser Surgery Center LLC', title: 'Physician-Owned, Single Specialty ASC', received: '11/18/2024', date: '2/4/2025', finding: 'Approved', county: 'Gwinnett', contact: 'M. Phagan' },
  { type: 'LNR-ASC', num: 'LNR-ASC2026003', facility: 'Atlanta South Gastroenterology, PC', title: 'Single Specialty ASC — Endoscopy', received: '2/19/2026', date: '4/7/2026', finding: 'Issued', county: 'Clayton', contact: 'R. Sinha' },
  { type: 'LNR-ASC', num: 'LNR-ASC2025014', facility: 'Center for Spine & Pain Medicine, PC', title: 'Single Specialty ASC — Pain Management', received: '10/3/2025', date: '12/18/2025', finding: 'Issued', county: 'Cobb', contact: 'B. Dennie' },
  { type: 'LNR-ASC', num: 'LNR-ASC2025009', facility: 'Gainesville Eye Associates, LLC', title: 'Single Specialty ASC — Ophthalmology', received: '7/15/2025', date: '9/22/2025', finding: 'Issued', county: 'Hall', contact: 'T. Branch' },
  { type: 'LNR-EQT', num: 'LNR-EQT2026008', facility: 'The Longstreet Clinic, PC', title: 'Acquisition of CT Scanner', received: '2/27/2026', date: '4/10/2026', finding: 'Issued', county: 'Hall', contact: 'M. Madison' },
  { type: 'LNR-EQT', num: 'LNR-EQT2025021', facility: 'The Emory Clinic', title: 'Replacement Linear Accelerator', received: '11/4/2025', date: '12/30/2025', finding: 'Issued', county: 'DeKalb', contact: 'K. Andrews' },
  { type: 'LNR-EQT', num: 'LNR-EQT2025014', facility: 'Harbin Clinic, LLC', title: 'Replacement of 1.5T MRI', received: '7/18/2025', date: '9/10/2025', finding: 'Issued', county: 'Floyd', contact: 'J. Herring' },
];

export function findingColor(f: string | null | undefined): string {
  return f === 'Approved' || f === 'Issued'
    ? '#10B981'
    : f === 'Denied'
      ? '#8E1B1F'
      : f === 'Pending'
        ? '#F59E0B'
        : 'var(--text2)';
}

// Case id <-> docket number mapping (mirrors the comp's CASE_TO_NUM).
export const CASE_TO_NUM: Record<string, string> = {
  'riverstone-imaging': '2026007',
  'three-rivers': '2026002',
  magnolia: '2026004',
  northridge: '2025028',
  cobblestone: '2025017',
  'coastal-empire': '2025017', // no live roll entry — nearest companion docket
};

export interface FixtureProceeding extends Proceeding {
  docketId: string;
  source: 'fixture';
  facility?: string;
  projectTitle?: string;
  headerNum?: string;
  county?: string;
}

/**
 * Resolve a docket id (route param) to a proceeding: the curated Riverstone
 * console for its ids, otherwise docketEngine.build over the docket roll —
 * exactly the comp's resolution order.
 */
export function fixtureGetProceeding(docketId: string): FixtureProceeding | null {
  const isRiverstone =
    docketId === 'riverstone-imaging' || docketId === '2026007' || docketId === 'CON2026007';
  if (isRiverstone) {
    return {
      ...RIVERSTONE_CON,
      docketId: '2026007',
      source: 'fixture',
      facility: 'Riverstone Imaging, LLC',
      projectTitle: 'Fixed 1.5T MRI — Bartow County',
      headerNum: 'CON 2026007',
      county: 'Bartow',
    };
  }
  const lookup = CASE_TO_NUM[docketId] ?? docketId;
  const rec = RECENT_DOCKETS.find((d) => d.num === lookup);
  if (!rec) return null;
  const proceeding = build(rec);
  if (!proceeding) return null;
  return {
    ...proceeding,
    docketId: rec.num!,
    source: 'fixture',
    facility: rec.facility ?? undefined,
    projectTitle: rec.title ?? undefined,
    headerNum: rec.type === 'CON' ? `CON ${rec.num}` : rec.num!,
    county: rec.county ?? undefined,
  };
}

/** Map a docket id back to a corpus case id when one exists. */
export function caseIdForDocket(docketId: string): string | null {
  if (docketId === 'riverstone-imaging' || docketId === '2026007' || docketId === 'CON2026007') {
    return 'riverstone-imaging';
  }
  const hit = Object.entries(CASE_TO_NUM).find(([, num]) => num === docketId);
  return hit ? hit[0] : CASES[docketId] ? docketId : null;
}

// ---------------------------------------------------------------------------
// Search scopes + facets (from the comp)
// ---------------------------------------------------------------------------

export const SCOPE_DEFS: Record<string, { label: string; types: string[] | null }> = {
  all: { label: 'All CON Sources', types: null },
  CON: { label: 'CON Determinations', types: ['CON'] },
  DET: { label: 'Determinations of Reviewability', types: ['DET', 'DET-EQT', 'DET-ASC'] },
  equipment: { label: 'Equipment (DET-EQT / LNR-EQT)', types: ['DET-EQT', 'LNR-EQT'] },
  asc: { label: 'ASC (DET-ASC / LNR-ASC)', types: ['DET-ASC', 'LNR-ASC'] },
};

export interface FacetDef {
  title: string;
  dim: string;
  items: { label: string; val: string; count: string }[];
  more: boolean;
}

export const FACET_DEFS: FacetDef[] = [
  {
    title: 'Docket Type',
    dim: 'dkt',
    items: [
      { label: 'CON — Certificate of Need', val: 'CON', count: '4,128' },
      { label: 'DET — Determination of Review.', val: 'DET', count: '4,028' },
      { label: 'DET-EQT — Equipment', val: 'DET-EQT', count: '801' },
      { label: 'DET-ASC — ASC', val: 'DET-ASC', count: '124' },
      { label: 'LNR-EQT — Letter of Nonrev., Equip.', val: 'LNR-EQT', count: '651' },
      { label: 'LNR-ASC — Letter of Nonrev., ASC', val: 'LNR-ASC', count: '364' },
    ],
    more: false,
  },
  {
    title: 'Source Type',
    dim: 'source',
    items: [
      { label: 'Agency Determinations', val: 'Agency Determinations', count: '1,204' },
      { label: 'Hearing Officer Decisions', val: 'Hearing Officer Decisions', count: '612' },
      { label: 'Commissioner Final Orders', val: 'Commissioner Final Orders', count: '288' },
      { label: 'Superior Court Orders', val: 'Superior Court Orders', count: '184' },
      { label: 'Appellate Opinions', val: 'Appellate Opinions', count: '130' },
    ],
    more: true,
  },
  {
    title: 'Court / Forum',
    dim: 'forum',
    items: [
      { label: 'DCH Planning', val: 'DCH Planning', count: '1,204' },
      { label: 'OSAH', val: 'OSAH', count: '612' },
      { label: 'DCH Commissioner', val: 'DCH Commissioner', count: '288' },
      { label: 'Superior Court', val: 'Superior Court', count: '184' },
      { label: 'Ga. Ct. App.', val: 'Ga. Ct. App.', count: '102' },
      { label: 'Ga. Sup. Ct.', val: 'Ga. Sup. Ct.', count: '28' },
    ],
    more: false,
  },
  {
    title: 'Service Category',
    dim: 'service',
    items: [
      { label: 'Imaging — MRI / CT / PET', val: 'Imaging', count: '418' },
      { label: 'Hospital Beds', val: 'Beds', count: '362' },
      { label: 'Ambulatory Surgery (ASC)', val: 'ASC', count: '301' },
      { label: 'Cardiac Catheterization', val: 'Cardiac', count: '188' },
      { label: 'Skilled Nursing / LTC', val: 'SNF', count: '141' },
    ],
    more: true,
  },
  {
    title: 'Outcome',
    dim: 'outcome',
    items: [
      { label: 'Granted', val: 'Granted', count: '1,128' },
      { label: 'Denied', val: 'Denied', count: '802' },
      { label: 'Reversed / Remanded', val: 'Reversed', count: '224' },
      { label: 'Affirmed', val: 'Affirmed', count: '341' },
      { label: 'Dismissed', val: 'Dismissed', count: '74' },
    ],
    more: false,
  },
  {
    title: 'Date Decided',
    dim: 'year',
    items: [
      { label: '2026', val: '2026', count: '64' },
      { label: '2025', val: '2025', count: '198' },
      { label: '2024', val: '2024', count: '256' },
      { label: '2020 – 2023', val: 'pre24', count: '912' },
      { label: 'Before 2020', val: 'pre20', count: '988' },
    ],
    more: false,
  },
  {
    title: 'Topic',
    dim: 'topic',
    items: [
      { label: 'III. Substantive Review', val: 'III', count: '1,012' },
      { label: 'V. Adjudication', val: 'V', count: '482' },
      { label: 'VI. Appellate Review', val: 'VI', count: '218' },
      { label: 'I. Jurisdiction', val: 'I', count: '184' },
    ],
    more: true,
  },
];

// ---------------------------------------------------------------------------
// Result cards (the comp's resultCards + CARD_TAGS, snippets as segments)
// ---------------------------------------------------------------------------

const hl = (t: string): Seg => ['hl', t];
const it = (t: string): Seg => ['i', t];

export const RESULT_CARDS: ResultCard[] = [
  {
    rank: 1,
    score: '98%',
    caseId: 'riverstone-imaging',
    docketId: '2026007',
    dktType: 'CON',
    dktNum: 'CON 23-0118 (now 2026007)',
    docType: 'Court of Appeals · Opinion',
    title: 'Riverstone Imaging, LLC v. Ga. Dep’t of Cmty. Health',
    cite: '372 Ga. App. 488, 902 S.E.2d 144',
    court: 'Ga. Ct. App.',
    date: 'Dec 4, 2025',
    outcome: 'Affirmed — Reversal of Final Decision',
    outcomeColor: '#10B981',
    flagGlyph: '!',
    flagBg: 'rgba(245,158,11,0.14)',
    flagColor: '#F59E0B',
    flagBorder: '#E5C97A',
    flagTitle: 'Caution — distinguished by later decision',
    snippet: [
      '… the Commissioner’s reliance on a five-county service area for the ',
      hl('MRI need methodology'),
      ' was not supported by ',
      hl('substantial evidence'),
      ' under O.C.G.A. § 31-6-44.1, where the record demonstrated that 78% of historical referrals originated from a three-county primary service area …',
    ],
    keys: [
      { num: 'CON III·7', label: 'Need / Utilization', id: 'iii-7' },
      { num: 'CON VI·24', label: 'Substantial Evidence', id: 'vi-24' },
      { num: 'CON IV·14', label: 'Imaging (MRI/CT/PET)', id: 'iv-14' },
    ],
    citedBy: 27,
    length: '14 pp.',
    fSource: 'Appellate Opinions',
    fForum: 'Ga. Ct. App.',
    fService: 'Imaging',
    fOutcome: 'Reversed',
    fYear: '2025',
    fTopic: 'VI',
    searchText:
      'riverstone imaging mri fixed need methodology substantial evidence service area bartow referral patterns reversed remanded rule 111-2-2-.40 31-6-44.1 court of appeals',
  },
  {
    rank: 2,
    score: '94%',
    caseId: 'three-rivers',
    docketId: '2026002',
    dktType: 'CON',
    dktNum: 'CON 23-0118',
    docType: 'DCH Commissioner · Final Decision',
    title: 'In re Application of Three Rivers Imaging, LLC',
    cite: 'CON No. 23-0118 (Final Order Aug. 7, 2024)',
    court: 'DCH Commissioner',
    date: 'Aug 7, 2024',
    outcome: 'Affirmed — Application Denied',
    outcomeColor: '#9B2C2C',
    flagGlyph: '●',
    flagBg: 'rgba(244,63,94,0.14)',
    flagColor: 'var(--accent-text)',
    flagBorder: '#E5C0C0',
    flagTitle: 'Negative treatment — reversed on review',
    snippet: [
      'Applicant failed to rebut the Department’s ',
      hl('MRI need methodology'),
      ' under Rule 111-2-2-.40 for the Bartow County primary service area; absent a demonstration that the existing fixed unit at Cartersville Medical Center is operating at or above the threshold utilization, no unmet ',
      hl('need'),
      ' has been shown …',
    ],
    keys: [
      { num: 'CON III·7', label: 'Need / Utilization', id: 'iii-7' },
      { num: 'CON IV·14', label: 'Imaging (MRI/CT/PET)', id: 'iv-14' },
    ],
    citedBy: 9,
    length: '32 pp.',
    fSource: 'Commissioner Final Orders',
    fForum: 'DCH Commissioner',
    fService: 'Imaging',
    fOutcome: 'Denied',
    fYear: '2024',
    fTopic: 'III',
    searchText:
      'three rivers imaging mri need methodology bartow utilization threshold commissioner final denied rule 111-2-2-.40 substantial evidence',
  },
  {
    rank: 3,
    score: '91%',
    caseId: 'cobblestone',
    docketId: '2025017',
    dktType: 'CON',
    dktNum: 'CON 2025017',
    docType: 'OSAH · Initial Decision',
    title: 'Cobblestone Surgical Partners, LLC v. Ga. Dep’t of Cmty. Health',
    cite: 'OSAH-DCH-CON-25-018-Kennedy',
    court: 'OSAH (Kennedy, ALJ)',
    date: 'Feb 14, 2025',
    outcome: 'Recommended — Grant of CON',
    outcomeColor: '#10B981',
    flagGlyph: '✓',
    flagBg: 'rgba(16,185,129,0.14)',
    flagColor: '#10B981',
    flagBorder: '#B7D6BE',
    flagTitle: 'Positive treatment — no negative history',
    snippet: [
      'The Department’s rigid application of a single-county service area, divorced from referral patterns and physician practice patterns, is inconsistent with the ',
      hl('substantial evidence'),
      ' standard articulated in ',
      it('Coastal Empire Hosp. Auth.'),
      ', and the ',
      hl('need methodology'),
      ' must account for the demonstrated travel patterns of the patient population …',
    ],
    keys: [
      { num: 'CON IV·13', label: 'Ambulatory Surgery', id: 'iv-13' },
      { num: 'CON III·10', label: 'Existing Alternatives', id: 'iii-10' },
      { num: 'CON V·21', label: 'Burden of Proof', id: 'v-21' },
    ],
    citedBy: 4,
    length: '47 pp.',
    fSource: 'Hearing Officer Decisions',
    fForum: 'OSAH',
    fService: 'ASC',
    fOutcome: 'Granted',
    fYear: '2025',
    fTopic: 'III',
    searchText:
      'cobblestone surgical partners ambulatory surgery center asc chatham substantial evidence need methodology service area osah burden of proof existing alternatives',
  },
  {
    rank: 4,
    score: '88%',
    caseId: 'magnolia',
    docketId: '2026004',
    dktType: 'CON',
    dktNum: 'CON 2026004',
    docType: 'Superior Court · Order',
    title: 'Magnolia Behavioral Health, LLC v. Ga. Dep’t of Cmty. Health',
    cite: 'No. 2024CV-3318 (Fulton Super. Ct.)',
    court: 'Fulton Super. Ct. (Welch, J.)',
    date: 'Nov 21, 2024',
    outcome: 'Reversed and Remanded',
    outcomeColor: '#F59E0B',
    flagGlyph: '!',
    flagBg: 'rgba(245,158,11,0.14)',
    flagColor: '#F59E0B',
    flagBorder: '#E5C97A',
    flagTitle: 'Caution — limited holding',
    snippet: [
      'The Court agrees with Petitioner that the agency’s adoption of a population-based ',
      hl('need methodology'),
      ' for psychiatric beds, without reference to the actual occupancy data of existing providers in DeKalb and Fulton Counties, fails the ',
      hl('substantial evidence'),
      ' standard …',
    ],
    keys: [
      { num: 'CON IV·11', label: 'Psychiatric / Behavioral', id: 'iv-11' },
      { num: 'CON VI·24', label: 'Substantial Evidence', id: 'vi-24' },
    ],
    citedBy: 6,
    length: '18 pp.',
    fSource: 'Superior Court Orders',
    fForum: 'Superior Court',
    fService: 'Beds',
    fOutcome: 'Reversed',
    fYear: '2024',
    fTopic: 'VI',
    searchText:
      'magnolia behavioral health psychiatric beds need methodology substantial evidence occupancy data superior court reversed remanded fulton dekalb',
  },
  {
    rank: 5,
    score: '86%',
    caseId: 'northridge',
    docketId: '2025028',
    dktType: 'CON',
    dktNum: 'CON 2025028',
    docType: 'DCH Planning · Initial Decision',
    title: 'In re Northridge Cardiac Servs., LLC — CON No. 24-0042',
    cite: 'DCH Init. Dec. Nov. 1, 2024',
    court: 'DCH Planning',
    date: 'Nov 1, 2024',
    outcome: 'Denied',
    outcomeColor: '#9B2C2C',
    flagGlyph: '●',
    flagBg: 'var(--surface2)',
    flagColor: 'var(--text2)',
    flagBorder: 'var(--border2)',
    flagTitle: 'No subsequent history',
    snippet: [
      'Applicant’s proposed cardiac catheterization service does not meet the ',
      hl('need methodology'),
      ' threshold of Rule 111-2-2-.22(4)(c). The five-year projected procedure volume of 612 cases falls below the minimum 750 …',
    ],
    keys: [
      { num: 'CON IV·15', label: 'Cardiac Cath / OHS', id: 'iv-15' },
      { num: 'CON III·7', label: 'Need / Utilization', id: 'iii-7' },
    ],
    citedBy: 2,
    length: '24 pp.',
    fSource: 'Agency Determinations',
    fForum: 'DCH Planning',
    fService: 'Cardiac',
    fOutcome: 'Denied',
    fYear: '2024',
    fTopic: 'III',
    searchText:
      'northridge cardiac catheterization need methodology threshold rule 111-2-2-.22 denied dch planning forsyth volume',
  },
  {
    rank: 6,
    score: '82%',
    caseId: 'coastal-empire',
    docketId: '2025017',
    dktType: 'CON',
    dktNum: 'CON 21-0044',
    docType: 'Court of Appeals · Opinion',
    title: 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC',
    cite: '358 Ga. App. 211, 854 S.E.2d 718',
    court: 'Ga. Ct. App.',
    date: 'Oct 19, 2023',
    outcome: 'Affirmed — Grant of CON',
    outcomeColor: '#10B981',
    flagGlyph: '✓',
    flagBg: 'rgba(16,185,129,0.14)',
    flagColor: '#10B981',
    flagBorder: '#B7D6BE',
    flagTitle: 'Positive treatment',
    snippet: [
      'The proper ',
      hl('need methodology'),
      ' must, at a minimum, take into account the demonstrated referral patterns and the ',
      hl('substantial evidence'),
      ' in the record of cross-county patient flow … Rule 111-2-2 does not require a hyper-mechanical application divorced from market reality.',
    ],
    keys: [
      { num: 'CON IV·12', label: 'Hospital Beds', id: 'iv-12' },
      { num: 'CON III·7', label: 'Need / Utilization', id: 'iii-7' },
      { num: 'CON VI·24', label: 'Substantial Evidence', id: 'vi-24' },
    ],
    citedBy: 41,
    length: '22 pp.',
    fSource: 'Appellate Opinions',
    fForum: 'Ga. Ct. App.',
    fService: 'Beds',
    fOutcome: 'Granted',
    fYear: 'pre24',
    fTopic: 'III',
    searchText:
      'coastal empire hospital authority piedmont coastal hospital beds need methodology substantial evidence referral patterns court of appeals affirmed grant',
  },
];

const STOPWORDS = new Set(['the', 'of', 'and', 'a', 'an', 'in', 'on', 'to', 'for', 'or']);

export interface FixtureSearchResult {
  cards: ResultCard[];
  queryDisplay: string;
}

/**
 * Client-side corpus search mirroring the comp: `docket-type:X` prefilter,
 * any-token match over searchText+title, facet selection filter, score sort.
 */
export function fixtureSearch(
  q: string,
  scope: string,
  facetSel: Record<string, boolean>,
): FixtureSearchResult {
  const rq = (q || '').trim();
  let queryDkt: string | null = null;
  let queryTokens: string[] = [];
  if (/^docket-type:/i.test(rq)) {
    queryDkt = rq.split(':')[1].trim().toUpperCase();
  } else if (rq) {
    queryTokens = rq
      .toLowerCase()
      .replace(/["'(),.]/g, ' ')
      .split(/\s+/)
      .filter((t) => t.length >= 3 && !STOPWORDS.has(t));
  }

  const selByDim: Record<string, string[]> = {};
  for (const g of FACET_DEFS) {
    for (const item of g.items) {
      if (facetSel[`${g.dim}|${item.val}`]) {
        (selByDim[g.dim] = selByDim[g.dim] || []).push(item.val);
      }
    }
  }

  const scopeTypes = (SCOPE_DEFS[scope] ?? SCOPE_DEFS.all).types;

  const dimVal = (card: ResultCard, dim: string): string | undefined =>
    ({
      dkt: card.dktType,
      source: card.fSource,
      forum: card.fForum,
      service: card.fService,
      outcome: card.fOutcome,
      year: card.fYear,
      topic: card.fTopic,
    })[dim];

  const cards = RESULT_CARDS.map((card) => {
    let score = 0;
    if (queryTokens.length) {
      const hay = `${card.searchText} ${card.title}`.toLowerCase();
      for (const t of queryTokens) if (hay.includes(t)) score++;
    }
    return { card, score };
  })
    .filter(({ card, score }) => {
      if (queryDkt && card.dktType !== queryDkt) return false;
      if (scopeTypes && !scopeTypes.includes(card.dktType)) return false;
      if (queryTokens.length && score === 0) return false;
      for (const dim of Object.keys(selByDim)) {
        const vals = selByDim[dim];
        if (vals.length && !vals.includes(dimVal(card, dim) ?? '')) return false;
      }
      return true;
    })
    .sort((a, b) => b.score - a.score)
    .map(({ card }, i) => ({ ...card, rank: i + 1 }));

  const queryDisplay = queryDkt
    ? (DOCKET_TYPES[queryDkt]?.full ?? queryDkt)
    : rq || 'All CON Sources';
  return { cards, queryDisplay };
}

// ---------------------------------------------------------------------------
// Home-screen fixture content (from the comp)
// ---------------------------------------------------------------------------

export const SAMPLE_QUERIES = [
  '"substantial evidence" need methodology',
  'Rule 111-2-2-.40 MRI',
  'standing competing applicant',
  'O.C.G.A. 31-6-44(c)',
];

export interface DocketTypeTile {
  type: string;
  label: string;
  full: string;
  fill: string;
  count: string;
}

export const DOCKET_TYPE_TILES: DocketTypeTile[] = [
  { type: 'CON', label: 'CON', full: 'Certificate of Need', fill: '#8E1B1F', count: '4,128' },
  { type: 'DET', label: 'DET', full: 'Determination of Reviewability', fill: '#F59E0B', count: '4,028' },
  { type: 'DET-EQT', label: 'DET·EQT', full: 'DOR — Equipment', fill: '#8B5CF6', count: '801' },
  { type: 'DET-ASC', label: 'DET·ASC', full: 'DOR — ASC', fill: '#10B981', count: '124' },
  { type: 'LNR-EQT', label: 'LNR·EQT', full: 'Letter of Nonrev. — Equip.', fill: '#8B5CF6', count: '651' },
  { type: 'LNR-ASC', label: 'LNR·ASC', full: 'Letter of Nonrev. — ASC', fill: '#3B82F6', count: '364' },
];

export interface RecentItem {
  title: string;
  cite: string;
  court: string;
  date: string;
  flagColor: string;
  action: string;
  badgeType: string | null; // docket type, or null for the OPINION chip
  caseId: string;
}

export const RECENT_ITEMS: RecentItem[] = [
  {
    title: 'Riverstone Imaging, LLC v. Ga. Dep’t of Cmty. Health',
    cite: '372 Ga. App. 488',
    court: 'Ga. Ct. App.',
    date: 'Dec 4, 2025',
    flagColor: '#F59E0B',
    action: 'Viewed',
    badgeType: null,
    caseId: 'riverstone-imaging',
  },
  {
    title: 'In re Application of Three Rivers Imaging, LLC',
    cite: 'CON No. 23-0118',
    court: 'DCH Commissioner',
    date: 'Aug 7, 2024',
    flagColor: 'var(--accent-text)',
    action: 'Annotated',
    badgeType: 'CON',
    caseId: 'three-rivers',
  },
  ...RECENT_DOCKETS.slice(0, 3).map((d) => ({
    title: `${d.facility} — ${d.title}`,
    cite: d.num ?? '',
    court: `DCH Planning · ${d.county} Co.`,
    date: String(d.received ?? ''),
    flagColor: findingColor(d.finding),
    action: d.finding ?? '',
    badgeType: d.type,
    caseId: d.num ?? '',
  })),
];

export interface WhatsNewItem {
  tag: string;
  tagColor: string;
  tagBg: string;
  date: string;
  lead?: string; // bold lead-in
  title: string;
  em?: boolean; // italicize the lead
}

export const WHATS_NEW: WhatsNewItem[] = [
  {
    tag: 'CON · Denied',
    tagColor: 'var(--accent-text)',
    tagBg: 'rgba(244,63,94,0.14)',
    date: 'Apr 14, 2026',
    lead: 'CON 2026004 — ',
    title:
      'Magnolia Behavioral Health, LLC: 48 psychiatric beds, Fulton/DeKalb PSA. Initial decision denying application issued.',
  },
  {
    tag: 'DET · Approved',
    tagColor: '#10B981',
    tagBg: 'rgba(16,185,129,0.14)',
    date: 'Apr 11, 2026',
    lead: 'DET2026003 — ',
    title: 'Northside Hospital, Inc.: conversion of skilled nursing beds approved as non-reviewable.',
  },
  {
    tag: 'DET-EQT · Pending',
    tagColor: '#8B5CF6',
    tagBg: 'rgba(139,92,246,0.14)',
    date: 'Apr 22, 2026',
    lead: 'DET-EQT2026062 — ',
    title: "Emory Saint Joseph's Hospital: replacement of da Vinci surgical robot under review.",
  },
  {
    tag: 'Ct. App.',
    tagColor: 'var(--accent-text)',
    tagBg: 'rgba(244,63,94,0.14)',
    date: 'Mar 12, 2026',
    lead: 'Riverstone Imaging v. DCH',
    em: true,
    title: ' — Ga. Supreme Court denies certiorari; Court of Appeals opinion stands.',
  },
  {
    tag: 'Rule Update',
    tagColor: '#F59E0B',
    tagBg: 'rgba(245,158,11,0.14)',
    date: 'Feb 28, 2026',
    title:
      'Ga. Comp. R. & Regs. 111-2-2-.40 — proposed amendments to MRI need methodology open for comment.',
  },
];
