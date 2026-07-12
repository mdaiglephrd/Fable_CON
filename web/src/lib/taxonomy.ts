/*
 * Topics & Key Numbers fixture data — the comp's TAXONOMY tree and the
 * curated key detail for CON III·7 (Need / Utilization), with a generated
 * fallback for every other key. Live mode maps GET /topics into the same
 * shapes (see views/Topics.tsx).
 */

export interface TaxonomyKey {
  id: string;
  num: string;
  label: string;
  count: number;
}

export interface TaxonomyTopic {
  id: string;
  numeral: string;
  title: string;
  count: number;
  keys: TaxonomyKey[];
}

export const TAXONOMY: TaxonomyTopic[] = [
  {
    id: 'i',
    numeral: 'I',
    title: 'Jurisdiction & Reviewability',
    count: 184,
    keys: [
      { num: 'CON I·1', id: 'i-1', label: 'Threshold for Review', count: 64 },
      { num: 'CON I·2', id: 'i-2', label: 'Letters of Non-Reviewability', count: 38 },
      { num: 'CON I·3', id: 'i-3', label: 'Statutorily Exempt Activities', count: 82 },
    ],
  },
  {
    id: 'ii',
    numeral: 'II',
    title: 'Application Process',
    count: 412,
    keys: [
      { num: 'CON II·4', id: 'ii-4', label: 'Letter of Intent', count: 92 },
      { num: 'CON II·5', id: 'ii-5', label: 'Batching Cycles', count: 118 },
      { num: 'CON II·6', id: 'ii-6', label: 'Competing Applications', count: 202 },
    ],
  },
  {
    id: 'iii',
    numeral: 'III',
    title: 'Substantive Review Criteria',
    count: 1012,
    keys: [
      { num: 'CON III·7', id: 'iii-7', label: 'Need / Utilization', count: 488 },
      { num: 'CON III·8', id: 'iii-8', label: 'Financial Feasibility', count: 211 },
      { num: 'CON III·9', id: 'iii-9', label: 'Quality of Care', count: 142 },
      { num: 'CON III·10', id: 'iii-10', label: 'Existing Alternatives', count: 171 },
    ],
  },
  {
    id: 'iv',
    numeral: 'IV',
    title: 'Service Categories',
    count: 2208,
    keys: [
      { num: 'CON IV·11', id: 'iv-11', label: 'Psychiatric / Behavioral', count: 184 },
      { num: 'CON IV·12', id: 'iv-12', label: 'Hospital Beds', count: 362 },
      { num: 'CON IV·13', id: 'iv-13', label: 'Ambulatory Surgery (ASC)', count: 301 },
      { num: 'CON IV·14', id: 'iv-14', label: 'Imaging — MRI / CT / PET', count: 418 },
      { num: 'CON IV·15', id: 'iv-15', label: 'Cardiac Cath / OHS', count: 188 },
      { num: 'CON IV·16', id: 'iv-16', label: 'Skilled Nursing / LTC', count: 322 },
      { num: 'CON IV·17', id: 'iv-17', label: 'Home Health / Hospice', count: 274 },
      { num: 'CON IV·18', id: 'iv-18', label: 'LTCH / IRF', count: 159 },
    ],
  },
  {
    id: 'v',
    numeral: 'V',
    title: 'Adjudication',
    count: 482,
    keys: [
      { num: 'CON V·19', id: 'v-19', label: 'Standing', count: 144 },
      { num: 'CON V·20', id: 'v-20', label: 'Intervention', count: 88 },
      { num: 'CON V·21', id: 'v-21', label: 'Burden of Proof', count: 162 },
      { num: 'CON V·22', id: 'v-22', label: 'Discovery in CON Hearings', count: 88 },
    ],
  },
  {
    id: 'vi',
    numeral: 'VI',
    title: 'Appellate Review',
    count: 218,
    keys: [
      { num: 'CON VI·23', id: 'vi-23', label: 'Standard of Review (Generally)', count: 78 },
      { num: 'CON VI·24', id: 'vi-24', label: 'Substantial Evidence', count: 92 },
      { num: 'CON VI·25', id: 'vi-25', label: 'Remand / Remedy', count: 28 },
      { num: 'CON VI·26', id: 'vi-26', label: 'Constitutional Challenges', count: 20 },
    ],
  },
];

export interface KeyAuthority {
  label: string;
  statuteId: string;
}

export interface KeyCase {
  caseId: string | null;
  title: string;
  cite: string;
  court: string;
  date: string;
  headnote: string;
  cited: number;
  depth: string;
  flagBg: string;
  flagBorder: string;
  flagTitle: string;
}

export interface KeyDetail {
  path: string;
  title: string;
  description: string;
  statutes: KeyAuthority[];
  rules: KeyAuthority[];
  subkeys: { num: string; label: string; count: number }[];
  caseCount: string;
  cases: KeyCase[];
}

const KEY_DETAILS: Record<string, KeyDetail> = {
  'iii-7': {
    path: 'CON · III · 7',
    title: 'Need / Utilization',
    description:
      'Cases construing the "need" element of CON review under O.C.G.A. § 31-6-42 and the service-specific need methodologies of Ga. Comp. R. & Regs. 111-2-2. Includes service-area definition, utilization thresholds, projection methodology, and the agency’s burden to articulate a reasoned basis for departing from an applicant’s referral data.',
    statutes: [
      { label: '§ 31-6-42 (Review Considerations)', statuteId: '31-6-42' },
      { label: '§ 31-6-43 (Approval / Denial)', statuteId: '31-6-43' },
    ],
    rules: [
      { label: 'Rule 111-2-2-.09 (Review Considerations)', statuteId: 'rule-111-2-2-.09' },
      { label: 'Rule 111-2-2-.40 (MRI)', statuteId: 'rule-111-2-2-.40' },
    ],
    subkeys: [
      { num: '7(a)', label: 'Service Area Definition', count: 188 },
      { num: '7(b)', label: 'Utilization Thresholds', count: 142 },
      { num: '7(c)', label: 'Projection Methodology', count: 92 },
      { num: '7(d)', label: 'Underserved Populations', count: 66 },
    ],
    caseCount: '488 headnoted cases',
    cases: [
      {
        caseId: 'riverstone-imaging',
        title: 'Riverstone Imaging, LLC v. Ga. Dep’t of Cmty. Health',
        cite: '372 Ga. App. 488 (2025)',
        court: 'Ga. Ct. App.',
        date: 'Dec. 4, 2025',
        headnote:
          'Service-area methodology that disregards uncontroverted referral data is not supported by substantial evidence; agency must articulate reasoned basis for departing from applicant’s PSA.',
        cited: 27,
        depth: 'In-depth',
        flagBg: 'rgba(245,158,11,0.14)',
        flagBorder: '#F59E0B',
        flagTitle: 'Caution — distinguished by later case',
      },
      {
        caseId: 'coastal-empire',
        title: 'Coastal Empire Hosp. Auth. v. Piedmont Coastal Health, LLC',
        cite: '358 Ga. App. 211 (2023)',
        court: 'Ga. Ct. App.',
        date: 'Oct. 19, 2023',
        headnote:
          'Need methodology must take into account demonstrated referral patterns and record evidence of cross-county patient flow. Rule 111-2-2 does not require hyper-mechanical application.',
        cited: 41,
        depth: 'In-depth',
        flagBg: 'rgba(16,185,129,0.14)',
        flagBorder: '#10B981',
        flagTitle: 'Positive treatment',
      },
      {
        caseId: 'three-rivers',
        title: 'In re Application of Three Rivers Imaging, LLC',
        cite: 'CON 23-0118 (DCH 2024)',
        court: 'DCH Commissioner',
        date: 'Aug. 7, 2024',
        headnote:
          'Applicant failed to rebut agency’s MRI need methodology under Rule 111-2-2-.40 for Bartow County PSA; existing fixed unit not shown to be at or above threshold utilization.',
        cited: 9,
        depth: 'Discussed',
        flagBg: 'rgba(244,63,94,0.14)',
        flagBorder: '#8E1B1F',
        flagTitle: 'Negative treatment — reversed',
      },
      {
        caseId: 'northridge',
        title: 'In re Northridge Cardiac Servs., LLC',
        cite: 'DCH 24-0042 (2024)',
        court: 'DCH Planning',
        date: 'Nov. 1, 2024',
        headnote:
          'Five-year projected cardiac catheterization volume of 612 cases falls below 750 minimum required under Rule 111-2-2-.22(4)(c); need not demonstrated.',
        cited: 2,
        depth: 'Cited',
        flagBg: 'var(--surface2)',
        flagBorder: 'var(--text3)',
        flagTitle: 'No subsequent history',
      },
      {
        caseId: 'magnolia',
        title: 'Magnolia Behavioral Health, LLC v. DCH',
        cite: '2024CV-3318 (Fulton Sup. Ct. 2024)',
        court: 'Sup. Ct.',
        date: 'Nov. 21, 2024',
        headnote:
          'Population-based need methodology for psychiatric beds, without occupancy data of existing providers, fails substantial-evidence standard.',
        cited: 6,
        depth: 'Discussed',
        flagBg: 'rgba(245,158,11,0.14)',
        flagBorder: '#F59E0B',
        flagTitle: 'Caution',
      },
    ],
  },
};

/** Find a key entry in the tree by id. */
export function findKey(keyId: string): { topic: TaxonomyTopic; key: TaxonomyKey } | null {
  for (const topic of TAXONOMY) {
    for (const key of topic.keys) {
      if (key.id === keyId) return { topic, key };
    }
  }
  return null;
}

/** Curated detail where authored; otherwise a generated fallback (the comp's `_fallback`). */
export function keyDetail(keyId: string): KeyDetail {
  const curated = KEY_DETAILS[keyId];
  if (curated) return curated;
  const hit = findKey(keyId);
  const key = hit?.key ?? TAXONOMY[2].keys[0];
  const [roman, num] = key.id.split('-');
  return {
    path: `CON · ${roman.toUpperCase()} · ${num ?? ''}`,
    title: key.label,
    description:
      `Headnoted determinations and judicial opinions addressing ${key.label.toLowerCase()} ` +
      'under O.C.G.A. § 31-6-1 et seq. and Ga. Comp. R. & Regs. 111-2-2.',
    statutes: [{ label: '§ 31-6-43 (Approval / Denial)', statuteId: '31-6-43' }],
    rules: [{ label: 'Ga. Comp. R. & Regs. 111-2-2', statuteId: 'rule-111-2-2-.09' }],
    subkeys: [],
    caseCount: `${key.count} headnoted cases`,
    cases: [],
  };
}

/** Default key when /topics is opened without a key id (matches the comp). */
export const DEFAULT_KEY_ID = 'iii-7';

/** Resolve a route param to a key id: a topic id ('iii') opens its first key. */
export function resolveTopicParam(param: string | undefined): string {
  if (!param) return DEFAULT_KEY_ID;
  if (findKey(param)) return param;
  const topic = TAXONOMY.find((t) => t.id === param.toLowerCase());
  if (topic && topic.keys.length) return topic.keys[0].id;
  return DEFAULT_KEY_ID;
}
