/*
 * Regulatory deadline rules — a hand port of common/deadline_rules.py used
 * ONLY in fixture mode so the Deadline Calculator runs standalone. Live mode
 * calls POST /deadlines/calculate, which computes from the same Python table;
 * the duplication is fixture-only and the Python module is the source of
 * truth (keep field-for-field in sync).
 */

export interface DeadlineRule {
  ruleId: string;
  docketFamily: 'CON' | 'DET';
  triggerEvent: string;
  offsetDays: number;
  basisStatute: string;
  description: string;
}

export const DEADLINE_RULES: DeadlineRule[] = [
  // --- CON family ---------------------------------------------------------
  {
    ruleId: 'con-challenge-window',
    docketFamily: 'CON',
    triggerEvent: 'Letter of determination',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description:
      'Request for an administrative hearing (challenge) is due within 30 days of the letter of determination.',
  },
  {
    ruleId: 'con-ho-appointment',
    docketFamily: 'CON',
    triggerEvent: 'Challenge filed',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description: 'Hearing officer appointment is due within 30 days of the challenge.',
  },
  {
    ruleId: 'con-hearing-window-open',
    docketFamily: 'CON',
    triggerEvent: 'Hearing officer appointed',
    offsetDays: 60,
    basisStatute: '31-6-44',
    description: 'Hearing window opens 60 days after the hearing officer appointment.',
  },
  {
    ruleId: 'con-hearing-window-close',
    docketFamily: 'CON',
    triggerEvent: 'Hearing officer appointed',
    offsetDays: 120,
    basisStatute: '31-6-44',
    description: 'Hearing window closes 120 days after the hearing officer appointment.',
  },
  {
    ruleId: 'con-ho-decision',
    docketFamily: 'CON',
    triggerEvent: 'Hearing concluded',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description: 'Hearing officer decision is due within 30 days of hearing conclusion.',
  },
  {
    ruleId: 'con-judicial-petition',
    docketFamily: 'CON',
    triggerEvent: 'Final agency decision',
    offsetDays: 30,
    basisStatute: '31-6-44.1',
    description:
      'Petition for judicial review is due within 30 days of the final agency decision.',
  },
  {
    ruleId: 'con-finality-default',
    docketFamily: 'CON',
    triggerEvent: 'Superior court docketing',
    offsetDays: 120,
    basisStatute: '50-13-19',
    description:
      '120-day default: if the superior court does not hear the case within 120 days of docketing, the agency decision is affirmed by operation of law (O.C.G.A. § 50-13-19, as modified by § 31-6-44.1).',
  },
  // --- DET family (subtypes fold onto DET) --------------------------------
  {
    ruleId: 'det-sufficiency',
    docketFamily: 'DET',
    triggerEvent: 'Request filed',
    offsetDays: 11,
    basisStatute: '31-6-2',
    description:
      'Sufficiency screen (administrative, informational) — opens the ~60-day review window.',
  },
  {
    ruleId: 'det-letter',
    docketFamily: 'DET',
    triggerEvent: 'Request filed',
    offsetDays: 60,
    basisStatute: '31-6-2',
    description: 'Letter of determination is due ~60 days from filing.',
  },
  {
    ruleId: 'det-challenge-window',
    docketFamily: 'DET',
    triggerEvent: 'Letter of determination',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description:
      'Challenge (request for an administrative hearing) is due within 30 days of the letter of determination.',
  },
  {
    ruleId: 'det-ho-appointment',
    docketFamily: 'DET',
    triggerEvent: 'Challenge filed',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description:
      'Hearing officer appointment is due within 30 days of the appeal — same mechanics as the CON administrative appeal.',
  },
  {
    ruleId: 'det-hearing-window-open',
    docketFamily: 'DET',
    triggerEvent: 'Hearing officer appointed',
    offsetDays: 60,
    basisStatute: '31-6-44',
    description: 'Hearing window opens 60 days after appointment — same mechanics as CON.',
  },
  {
    ruleId: 'det-hearing-window-close',
    docketFamily: 'DET',
    triggerEvent: 'Hearing officer appointed',
    offsetDays: 120,
    basisStatute: '31-6-44',
    description: 'Hearing window closes 120 days after appointment — same mechanics as CON.',
  },
  {
    ruleId: 'det-ho-decision',
    docketFamily: 'DET',
    triggerEvent: 'Hearing concluded',
    offsetDays: 30,
    basisStatute: '31-6-44',
    description:
      'Hearing officer decision is due within 30 days of hearing conclusion; under HB 1339 the HO decision is the final agency decision.',
  },
  {
    ruleId: 'det-judicial-petition',
    docketFamily: 'DET',
    triggerEvent: 'Final agency decision',
    offsetDays: 30,
    basisStatute: '31-6-44.1',
    description:
      'Petition for judicial review is due within 30 days of the final agency decision.',
  },
  {
    ruleId: 'det-finality-default',
    docketFamily: 'DET',
    triggerEvent: 'Superior court docketing',
    offsetDays: 120,
    basisStatute: '50-13-19',
    description:
      '120-day default finality on judicial review (O.C.G.A. § 50-13-19, as modified by § 31-6-44.1).',
  },
];

const ACRONYMS: Record<string, string> = { ho: 'HO', dch: 'DCH', con: 'CON', det: 'DET', lnr: 'LNR' };

/** Fold a docket family onto the family that owns its deadline rules. */
export function baseFamily(family: string): 'CON' | 'DET' | null {
  if (family === 'CON') return 'CON';
  if (['DET', 'DET-EQT', 'DET-ASC', 'LNR-ASC', 'LNR-EQT'].includes(family)) return 'DET';
  return null;
}

/** Short human label from a rule id ('con-ho-appointment' -> 'HO Appointment'). */
function humanize(ruleId: string): string {
  let parts = ruleId.split('-');
  if (parts[0] === 'con' || parts[0] === 'det') parts = parts.slice(1);
  return parts.map((p) => ACRONYMS[p] ?? p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
}

/** The trigger events defined for a family, in rule-table order (deduped). */
export function triggerEventsFor(family: string): string[] {
  const fam = baseFamily(family);
  if (!fam) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const rule of DEADLINE_RULES) {
    if (rule.docketFamily === fam && !seen.has(rule.triggerEvent)) {
      seen.add(rule.triggerEvent);
      out.push(rule.triggerEvent);
    }
  }
  return out;
}

export interface ComputedDeadlineLocal {
  label: string;
  dueDate: Date;
  basisStatute: string;
  description: string;
}

/**
 * Resolve every deadline rule for (family, triggerEvent) against `base` —
 * same semantics as common/deadline_rules.py compute_deadlines.
 */
export function computeDeadlines(
  family: string,
  triggerEvent: string,
  base: Date,
): ComputedDeadlineLocal[] {
  const fam = baseFamily(family);
  if (!fam) return [];
  const out: ComputedDeadlineLocal[] = [];
  for (const rule of DEADLINE_RULES) {
    if (rule.docketFamily === fam && rule.triggerEvent === triggerEvent) {
      const due = new Date(base.getTime());
      due.setDate(due.getDate() + rule.offsetDays);
      out.push({
        label: humanize(rule.ruleId),
        dueDate: due,
        basisStatute: rule.basisStatute,
        description: rule.description,
      });
    }
  }
  return out;
}
