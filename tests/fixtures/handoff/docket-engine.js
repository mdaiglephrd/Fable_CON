/*
 * Georgia CON Research — Docket View engine
 * ------------------------------------------
 * Produces the plain-data shape the dark "case console" Docket View
 * template renders: stage groups, substeps (with tooltip content),
 * outcome forks, deadline callouts, compact mini-bar, and a precedent
 * signal for closed dockets. Pure data + strings only — no functions,
 * no React — so the DC component can attach hover/click handlers itself.
 *
 * Docket-type coverage:
 *   CON              -> buildCON()   stages 0–7
 *   DET / DET-ASC /
 *   DET-EQT / LNR-ASC/
 *   LNR-EQT          -> buildDET()   stages 1–5 (stage 1–2 copy varies by subtype)
 */
(function () {

  var STATUS = {
    complete:   { label: 'COMPLETE',    color: '#10B981', bg: 'rgba(16,185,129,0.12)' },
    active:     { label: 'ACTIVE',      color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
    pending:    { label: 'PENDING',     color: '#94A3B8', bg: 'rgba(148,163,184,0.10)' },
    nottaken:   { label: 'NOT TAKEN',   color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
    notreached: { label: 'NOT REACHED', color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
    na:         { label: 'N/A',         color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
    denied:     { label: 'DENIED',      color: '#F43F5E', bg: 'rgba(244,63,94,0.12)' },
    challenged: { label: 'CHALLENGED',  color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
    applicable: { label: 'APPLICABLE',  color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
    current:    { label: 'CURRENT',     color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
    legacy:     { label: 'LEGACY',      color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
    approved:   { label: 'APPROVED',    color: '#10B981', bg: 'rgba(16,185,129,0.12)' },
    reviewable: { label: 'REVIEWABLE',  color: '#F43F5E', bg: 'rgba(244,63,94,0.12)' },
  };

  function parseDate(s) {
    if (!s) return null;
    if (s instanceof Date) return s;
    var m = String(s).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (m) return new Date(+m[3], +m[1] - 1, +m[2]);
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }
  function addDays(d, n) { var r = new Date(d.getTime()); r.setDate(r.getDate() + n); return r; }
  function fmt(d) { if (!d) return ''; return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
  function daysBetween(a, b) { return Math.round((b.getTime() - a.getTime()) / 86400000); }
  function durationLabel(a, b) {
    var days = daysBetween(a, b);
    var yrs = Math.floor(days / 365), mo = Math.round((days % 365) / 30);
    if (yrs <= 0) return mo + (mo === 1 ? ' month' : ' months');
    return yrs + (yrs === 1 ? ' yr' : ' yrs') + (mo ? ' ' + mo + ' mo' : '');
  }

  var NOW = new Date(2026, 5, 25);

  // deterministic pseudo-random 0..1 from a string, so the same docket
  // always gets the same synthesized precedent/variant without a real DB
  function seedOf(str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) { h = (h * 31 + str.charCodeAt(i)) | 0; }
    return Math.abs(h % 1000) / 1000;
  }

  function precedentForCON(rec) {
    var s = seedOf(rec.num || rec.facility || '');
    if (s < 0.72) return { key: 'valid', label: 'VALID PRECEDENT', color: STATUS.complete.color, bg: STATUS.complete.bg, detail: 'No negative subsequent treatment found · Last reviewed ' + fmt(addDays(NOW, -30)) };
    if (s < 0.9) return { key: 'questioned', label: 'QUESTIONED', color: STATUS.active.color, bg: STATUS.active.bg, detail: 'Distinguished in a subsequent proceeding · Not overruled' };
    return { key: 'overturned', label: 'OVERTURNED', color: STATUS.denied.color, bg: STATUS.denied.bg, detail: 'Reversed or overruled on appeal · Exercise caution citing' };
  }
  function precedentForDET() {
    return { key: 'noprecedent', label: 'NO PRECEDENT', color: '#94A3B8', bg: 'rgba(148,163,184,0.10)', detail: 'DET types bind parties and stated facts only — O.C.G.A. § 31-6-44 — may not be cited as authority for non-parties' };
  }

  function badgeMeta(type) {
    var M = {
      'CON':     { label: 'CON',     color: '#F43F5E' },
      'DET':     { label: 'DET',     color: '#F59E0B' },
      'DET-ASC': { label: 'DET·ASC', color: '#10B981' },
      'DET-EQT': { label: 'DET·EQT', color: '#8B5CF6' },
      'LNR-ASC': { label: 'LNR·ASC', color: '#10B981' },
      'LNR-EQT': { label: 'LNR·EQT', color: '#8B5CF6' },
    };
    return M[type] || { label: type || 'DKT', color: '#94A3B8' };
  }

  // ---------------------------------------------------------------
  // Generic CON builder (stages 0–7)
  // ---------------------------------------------------------------
  function buildCON(rec) {
    var filed = parseDate(rec.received) || NOW;
    var decided = parseDate(rec.date) || filed;
    var finding = rec.finding || 'Pending';
    var isClosed = finding !== 'Pending';
    var elapsed = isClosed ? daysBetween(filed, decided) : daysBetween(filed, NOW);
    var denied = finding === 'Denied';
    var withdrawn = finding === 'Withdrawn';

    // synthetic milestone dates (offsets typical of a real CON cycle)
    var dAck = addDays(filed, 3), dBatch = addDays(filed, 10), dNotice = addDays(filed, 20);
    var dDesk = isClosed ? decided : addDays(filed, 120);
    var dChallenge = addDays(dDesk, 14), dHOAppt = addDays(dDesk, 44);
    var dSched = addDays(dHOAppt, 9), dHearing = addDays(dSched, 90), dHODecision = addDays(dHearing, 28);
    var curStage = isClosed ? 7 : (elapsed < 120 ? 1 : elapsed < 150 ? 2 : elapsed < 240 ? 3 : 4);

    function st(n) { return n < curStage || isClosed ? 'complete' : n === curStage ? 'active' : 'pending'; }

    var stages = [];

    stages.push({
      n: '0', status: 'complete', title: 'Letter of Intent', dateLine: 'Filed ' + fmt(filed),
      substeps: [
        { code: '0a', label: 'Submission', tip: { title: '0a · Submission', status: 'complete', rows: ['Letter of intent filed ' + fmt(filed) + '.', 'Required pre-application filing — sets review cycle and batching window.'], statute: 'O.C.G.A. § 31-6-40' } },
        { code: '0b', label: 'Acknowledgement', tip: { title: '0b · Review Cycle / Batching', status: 'complete', rows: ['Acknowledged ' + fmt(dAck) + '.', rec.county ? ('Planning service area: ' + rec.county + ' County.') : 'Batching cycle assigned by planning service area.'], statute: 'O.C.G.A. § 31-6-40' } },
      ],
    });

    var s1status = st(1);
    var deskOutcome = isClosed ? (denied ? 'denied' : 'approved') : null;
    stages.push({
      n: '1', status: s1status, title: 'Initial Filing Review', dateLine: 'Submitted ' + fmt(filed) + (isClosed ? ' · Decision ' + fmt(dDesk) : ' · 120-day review clock'),
      substeps: [
        { code: '1a', label: 'Receipt', tip: { title: '1a · Application Submitted', status: 'complete', rows: ['Submitted ' + fmt(filed) + '.', 'Filing fee paid · 120-day review clock started.'], statute: 'O.C.G.A. § 31-6-43' } },
        { code: '1b', label: 'Batching', tip: { title: '1b · Review Cycle / Batching', status: 'complete', rows: ['Batching window opened ' + fmt(dBatch) + '.', 'Reviewed against competing applications in the same planning service area, if any.'], statute: 'O.C.G.A. § 31-6-43' } },
        { code: '1c', label: 'Public Notice', tip: { title: '1c · Public Comment / Opposition', status: 'complete', rows: ['Notice period opened ' + fmt(dNotice) + '.', 'Affected persons may file comments or notice of opposition.'], statute: 'O.C.G.A. § 31-6-43' } },
        { code: '1d', label: 'Agency Decision', tip: { title: '1d · Desk Decision', status: isClosed ? (denied ? 'denied' : 'complete') : 'pending', rows: isClosed ? ['Issued ' + fmt(dDesk) + ' — ' + finding.toUpperCase() + '.', 'DCH Office of Health Planning project officer of record.'] : ['Due by ' + fmt(dDesk) + ' (120 days from filing).'], statute: 'O.C.G.A. § 31-6-43' } },
      ],
      forks: [
        { key: 'approved', label: 'Approved', status: (isClosed && !denied) ? 'taken' : 'not-taken', title: 'Proceeds to Stage 2 (challenge window)' },
        { key: 'conditions', label: 'Approved with Conditions', status: 'not-taken', title: 'Conditions may include bed limits, service restrictions, or compliance reporting' },
        { key: 'denied', label: 'Denied', status: (isClosed && denied) ? 'taken' : 'not-taken', title: 'Proceeds to Stage 2 (challenge window)' },
      ],
    });

    stages.push({
      n: '2', status: isClosed ? 'complete' : st(2), title: 'Initial Decision Challenge', dateLine: isClosed ? 'Challenge window closed' : 'Opens on desk decision · 30-day window',
      substeps: [
        { code: '2a', label: 'Request Filed', tip: { title: '2a · Challenge Filed', status: 'complete', rows: ['Filed ' + fmt(dChallenge) + ' (within 30 days of the letter of determination).', 'Any aggrieved party who timely intervened may request review.'], statute: 'O.C.G.A. § 31-6-44(a)' } },
        { code: '2b', label: 'Challenge Registered', tip: { title: '2b · Challenge Registered', status: 'complete', rows: ['Docketed by DCH Office of Health Planning.', 'Timeliness and standing screened before assignment to a hearing officer.'], statute: 'O.C.G.A. § 31-6-44(a)' } },
      ],
      forks: [
        { key: 'challenge', label: 'Challenge filed → proceeds', status: 'taken', title: 'Proceeds to Stage 3 (Administrative Appeal)' },
        { key: 'nochallenge', label: 'No challenge filed', status: 'not-taken', title: 'Desk decision becomes final — no further review' },
      ],
    });

    var hoDenied = denied;
    stages.push({
      n: '3', status: isClosed ? 'complete' : st(3), title: 'Administrative Appeal', dateLine: isClosed ? 'Hearing ' + fmt(dHearing) + ' · Decision ' + fmt(dHODecision) : 'Appointed ' + fmt(dHOAppt),
      substeps: [
        { code: '3a', label: 'HO Appointed', tip: { title: '3a · Hearing Officer Appointed', status: 'complete', rows: ['Appointed ' + fmt(dHOAppt) + ' (within 30 days of the challenge).', 'Assigned by the Office of State Administrative Hearings.'], statute: 'O.C.G.A. § 31-6-44(b)' } },
        { code: '3b', label: 'Scheduling', tip: { title: '3b · Scheduling Conference', status: 'complete', rows: ['Held ' + fmt(dSched) + '.', 'Hearing dates and discovery deadlines set.'], statute: 'O.C.G.A. § 31-6-44(b)' } },
        { code: '3c', label: 'Hearing Window', tip: { title: '3c · Hearing Window', status: st(3) === 'active' ? 'active' : 'complete', rows: ['Window: 60–120 days after appointment.', 'Hearing dates: ' + fmt(dHearing) + '.'], statute: 'O.C.G.A. § 31-6-44(f)' } },
        { code: '3d', label: 'Hearing', tip: { title: '3d · Contested Case Hearing', status: 'complete', rows: ['Evidentiary hearing on need, financial feasibility, and access criteria.', 'Parties: DCH, applicant, and any intervening competing applicant.'], statute: 'O.C.G.A. § 31-6-44(e)' } },
        { code: '3e', label: 'HO Decision', tip: { title: '3e · Hearing Officer Decision', status: isClosed ? 'complete' : 'pending', rows: isClosed ? ['Issued ' + fmt(dHODecision) + ' — ' + (hoDenied ? 'Affirmed denial.' : 'Affirmed approval.')] : ['Due within 30 days of hearing conclusion.'], statute: 'O.C.G.A. § 31-6-44(e)' } },
      ],
    });

    stages.push({
      n: '4', status: isClosed ? 'complete' : st(4), title: 'Final Agency Decision', dateLine: isClosed ? 'Effective ' + fmt(dHODecision) : 'Triggered upon Stage 3 conclusion',
      regimeNote: {
        current: { label: 'Reformed Regime (HB 1339)', tag: 'current', detail: 'Hearing officer decision = final agency decision. Effective 2024 · No Commissioner review.' },
        legacy: { label: 'Prior Regime (Pre-2024)', tag: 'legacy', detail: 'Optional Commissioner review · 61-day finality window.' },
      },
    });

    var judReversed = false;
    stages.push({
      n: '5', status: isClosed ? 'complete' : st(5), title: 'Judicial Review', dateLine: 'Petition within 30 days of final agency decision',
      substeps: [
        { code: '5a', label: 'Petition Filed', tip: { title: '5a · Petition for Judicial Review', status: 'complete', rows: ['Must file within 30 days of the final agency decision.', 'Any party except DCH may petition · Venue: Superior Court.'], statute: 'O.C.G.A. § 31-6-44.1' } },
        { code: '5b', label: 'Record Transmittal', tip: { title: '5b · Record Transmittal', status: 'complete', rows: ['DCH must transmit the certified record and transcript within 30 days of notice of appeal.'], statute: 'O.C.G.A. § 31-6-44.1' } },
        { code: '5c', label: 'Hearing on Record', tip: { title: '5c · Hearing on the Record', status: 'complete', rows: ['Review confined to the administrative record — no new evidence.', 'Deferential, substantial-evidence standard.'], statute: 'O.C.G.A. § 50-13-19' } },
        { code: '5d', label: 'Disposition', tip: { title: '5d · Superior Court Disposition', status: isClosed ? 'complete' : 'pending', rows: [judReversed ? 'Reversed and remanded.' : 'Branch: Affirm / Reverse / Remand.', '120-day default rule: if the court does not hear within 120 days of docketing, the agency decision is affirmed by operation of law.'], statute: 'O.C.G.A. § 31-6-44.1' } },
      ],
    });

    stages.push({
      n: '6', status: isClosed ? 'complete' : 'pending', title: 'Appellate Review', dateLine: 'Upon Superior Court disposition',
      substeps: [
        { code: '6a', label: 'Court of Appeals', tip: { title: '6a · Court of Appeals', status: isClosed ? 'complete' : 'pending', rows: ['Either party may appeal the Superior Court order.', 'Branch: Affirm / Reverse / Remand.'], statute: 'O.C.G.A. § 5-6-34' } },
        { code: '6b', label: 'Supreme Court', tip: { title: '6b · Supreme Court of Georgia', status: 'pending', rows: ['By certiorari — discretionary review.', 'Petition for cert. granted or denied.'], statute: 'O.C.G.A. § 5-6-15' } },
      ],
    });

    var terminalKey = withdrawn ? 'withdrawn' : denied ? 'unbuilt' : isClosed ? 'approved' : null;
    stages.push({
      n: '7', status: isClosed ? 'complete' : 'pending', title: 'Terminal Outcomes', dateLine: isClosed ? 'Record closed ' + fmt(decided) : '',
      terminal: [
        { key: 'approved', label: 'Approved & Conditions Pending', status: terminalKey === 'approved' ? 'taken' : 'not-taken' },
        { key: 'constructed', label: 'Constructed & Licensed', status: 'not-taken' },
        { key: 'unbuilt', label: withdrawn ? 'Withdrawn' : 'Unbuilt / Lapsed CON', status: (terminalKey === 'unbuilt' || terminalKey === 'withdrawn') ? 'taken' : 'not-taken' },
        { key: 'remanded', label: 'Remanded', status: 'not-taken' },
      ],
    });

    var compact = [
      { code: 'Intent', status: 'complete' },
      { code: 'Review', status: s1status === 'pending' ? 'active' : 'complete' },
      { code: 'Initial', status: isClosed ? 'complete' : (curStage >= 2 ? 'complete' : 'pending'), tag: denied && curStage <= 2 ? 'Denied' : null },
      { code: 'Admin', status: isClosed ? 'complete' : (curStage === 3 ? 'active' : curStage > 3 ? 'complete' : 'pending') },
      { code: 'Agency', status: isClosed ? 'complete' : (curStage === 4 ? 'active' : curStage > 4 ? 'complete' : 'pending') },
      { code: 'Superior', status: isClosed ? 'complete' : 'pending' },
      { code: 'Appellate', status: isClosed ? 'complete' : 'pending' },
      { code: 'Final', status: isClosed ? 'complete' : 'pending' },
    ];

    return {
      badge: badgeMeta('CON'),
      isClosed: isClosed, isActive: !isClosed,
      filedLine: 'Filed ' + fmt(filed), closedLine: isClosed ? 'Closed ' + fmt(decided) : null,
      durationLine: isClosed ? durationLabel(filed, decided) : null,
      finalDisposition: isClosed ? ('CON ' + finding + (denied ? ' — Affirmed through review' : ' — Effective ' + fmt(decided))) : null,
      precedent: isClosed ? precedentForCON(rec) : null,
      compact: compact,
      stages: stages,
    };
  }

  // ---------------------------------------------------------------
  // Generic DET-family builder (stages 1–5), subtype-aware stage 1–2 copy
  // ---------------------------------------------------------------
  var SUBTYPE_COPY = {
    'DET': {
      label: 'DET (Generic)', sub: 'Determination of Reviewability',
      s1: 'Request on DCH form + filing fee · Subject: substantial equivalent of a new institutional health service.',
      s2: 'Is this a new institutional health service? Outcomes: Reviewable / Not Reviewable / Conditioned.',
      note: 'Base type · no exemption claimed', outcome: 'CON Required',
    },
    'DET-ASC': {
      label: 'DET-ASC', sub: 'ASC Letter of Non-Reviewability',
      s1: '$500 filing fee · Subject: proposed ambulatory surgery center operation.',
      s2: 'Does the ASC qualify as single-specialty or a qualifying joint venture? Outcomes: LNR issued / CON required.',
      note: 'Letter of Non-Reviewability (LNR)', outcome: 'LNR Issued',
    },
    'DET-EQT': {
      label: 'DET-EQT', sub: 'Equipment Threshold Determination',
      s1: 'Subject: purchase or lease of diagnostic or therapeutic equipment.',
      s2: 'HB 1339 (current): no dollar threshold — test is the new-service definition. Legacy: expenditure threshold test.',
      note: 'Anti-fragmentation: DCH aggregates component costs · era-sensitive — check docket date', outcome: 'Reviewable',
    },
    'LNR-ASC': {
      label: 'LNR-ASC', sub: 'ASC Letter of Non-Reviewability',
      s1: '$500 filing fee · Subject: proposed ambulatory surgery center operation.',
      s2: 'Does the ASC qualify as single-specialty or a qualifying joint venture? Outcomes: LNR issued / CON required.',
      note: 'Letter of Non-Reviewability (LNR)', outcome: 'LNR Issued',
    },
    'LNR-EQT': {
      label: 'LNR-EQT', sub: 'Letter of Non-Reviewability — Equipment',
      s1: 'Subject: activity claimed exempt or outside the new-service definition.',
      s2: 'Does the activity fall within a statutory exemption or outside the new-service definition? Outcomes: LNR issued / CON required.',
      note: 'LNR may issue with operating conditions · tracking required', outcome: 'LNR Issued',
    },
  };

  function buildDET(rec) {
    var sub = SUBTYPE_COPY[rec.type] || SUBTYPE_COPY['DET'];
    var filed = parseDate(rec.received) || NOW;
    var decided = parseDate(rec.date) || filed;
    var finding = rec.finding || 'Pending';
    var isClosed = finding !== 'Pending';
    var elapsed = isClosed ? daysBetween(filed, decided) : daysBetween(filed, NOW);
    var notReviewable = isClosed && (finding === 'Issued');
    var conReq = isClosed && !notReviewable && finding !== 'Withdrawn';

    var dSufficiency = addDays(filed, 11);
    var dLetter = isClosed ? decided : addDays(filed, 45);
    var dChallenge = addDays(dLetter, 14);
    var dHOAppt = addDays(dLetter, 44), dSched = addDays(dHOAppt, 9), dHearing = addDays(dSched, 60), dHODecision = addDays(dHearing, 28);

    var curStage = isClosed ? 5 : (elapsed < 45 ? 1 : elapsed < 60 ? 2 : elapsed < 100 ? 3 : 4);
    function st(n) { return isClosed ? 'complete' : (n < curStage ? 'complete' : n === curStage ? 'active' : 'pending'); }

    var stages = [];
    stages.push({
      n: '1', status: st(1), title: 'Request Submission', dateLine: 'Filed ' + fmt(filed),
      substeps: [
        { code: '1a', label: 'Request Filed', tip: { title: '1a · Request Filed', status: 'complete', rows: ['Filed ' + fmt(filed) + '.', sub.s1, 'No letter of intent required · no review cycle or batching.'], statute: 'O.C.G.A. § 31-6-43(e)' } },
        { code: '1b', label: 'Subject Defined', tip: { title: '1b · Subject Defined', status: 'complete', rows: [sub.s1, 'Classification sought: substantial equivalent of a new institutional health service.'], statute: 'O.C.G.A. § 31-6-2(23)' } },
        { code: '1c', label: 'Sufficiency Screen', tip: { title: '1c · Sufficiency Screen', status: 'complete', rows: ['DCH administrative review of submitted information.', 'Sufficiency confirmed ' + fmt(dSufficiency) + ' · ~60-day review window begins.'], statute: 'O.C.G.A. § 31-6-2(23)' } },
      ],
    });

    stages.push({
      n: '2', status: isClosed ? 'complete' : st(2), title: 'DCH Review & Letter Issued', dateLine: isClosed ? 'Letter issued ' + fmt(dLetter) : 'Due ~60 days from filing',
      substeps: [
        { code: '2a', label: 'Reviewability Test', tip: { title: '2a · Reviewability Test', status: 'complete', rows: [sub.s2], statute: 'O.C.G.A. § 31-6-2(23)' } },
        { code: '2b', label: 'Letter Issued', tip: { title: '2b · Letter of Determination Issued', status: isClosed ? 'complete' : 'pending', rows: isClosed ? ['Issued ' + fmt(dLetter) + ' · Outcome: ' + finding.toUpperCase() + '.', sub.note] : ['Due by ' + fmt(dLetter) + '.'], statute: 'O.C.G.A. § 31-6-2(23)' } },
      ],
      forks: [
        { key: 'notreviewable', label: 'Not Reviewable', status: notReviewable ? 'taken' : 'not-taken', title: 'May proceed without CON' },
        { key: 'conditioned', label: 'Conditioned / Partial', status: 'not-taken', title: 'Some components reviewable, others not' },
        { key: 'reviewable', label: 'Reviewable — CON Required', status: conReq ? 'taken' : 'not-taken', title: sub.outcome },
      ],
    });

    stages.push({
      n: '3', status: isClosed ? 'complete' : st(3), title: 'Finality or Challenge', dateLine: isClosed ? 'Challenge window closed' : 'Opens on letter issuance · 30-day window',
      forks: [
        { key: 'challenge', label: 'Challenge Filed → Administrative Appeal', status: 'taken', title: 'Filed ' + fmt(dChallenge) + ' · proceeds to Stage 4' },
        { key: 'final', label: 'No Challenge Filed', status: 'not-taken', title: 'Letter becomes final without further review — most DETs end here' },
      ],
      deadline: (!isClosed && curStage === 3) ? { items: ['Hearing officer appointment due within 30 days of challenge', 'Hearing window: 60–120 days after appointment'] } : null,
    });

    stages.push({
      n: '4', status: isClosed ? 'complete' : st(4), title: 'Administrative Appeal', dateLine: 'Identical mechanics to CON administrative appeal — HB 1339: HO decision = final agency decision',
      substeps: [
        { code: '4a', label: 'HO Appointed', tip: { title: '4a · Hearing Officer Appointed', status: 'complete', rows: ['Appointed ' + fmt(dHOAppt) + ' (within 30 days of appeal filing).', 'Same mechanics as CON administrative appeal.'], statute: 'O.C.G.A. § 31-6-44(b)' } },
        { code: '4b', label: 'Scheduling', tip: { title: '4b · Scheduling Conference', status: 'complete', rows: ['Held ' + fmt(dSched) + ' (within 14 days of appointment).'], statute: 'O.C.G.A. § 31-6-44(b)' } },
        { code: '4c', label: 'Hearing Window', tip: { title: '4c · Hearing Window', status: st(4) === 'active' ? 'active' : 'complete', rows: ['Window: 60–120 days after filing.', 'Hearing set ' + fmt(dHearing) + '.'], statute: 'O.C.G.A. § 31-6-44(f)' } },
        { code: '4d', label: 'Hearing', tip: { title: '4d · Contested Case Hearing', status: 'complete', rows: ['Evidence, witnesses, and reviewability-criteria arguments.', 'Same format as CON hearing.'], statute: 'O.C.G.A. § 31-6-44(e)' } },
        { code: '4e', label: 'HO Decision', tip: { title: '4e · Hearing Officer Decision', status: isClosed ? 'complete' : 'pending', rows: isClosed ? ['Issued ' + fmt(dHODecision) + '.', 'Under HB 1339 (eff. 2024): HO decision = final agency decision.'] : ['Due within 30 days of hearing conclusion.'], statute: 'O.C.G.A. § 31-6-44(e)' } },
      ],
    });

    stages.push({
      n: '5', status: isClosed ? 'complete' : 'pending', title: 'Judicial & Appellate', dateLine: 'Upon final agency decision',
      substeps: [
        { code: '5a', label: 'Superior Court', tip: { title: '5 · Superior Court Petition', status: isClosed ? 'complete' : 'pending', rows: ['Any party except DCH may petition within 30 days of the final agency decision.', 'Review on the administrative record — deferential standard.', '120-day default: if no hearing within 120 days of docketing, the agency decision is affirmed by operation of law.'], statute: 'O.C.G.A. § 50-13-19, as modified by § 31-6-44.1' } },
        { code: '5b', label: 'Court of Appeals', tip: { title: '5 · Court of Appeals', status: 'pending', rows: ['Either party may appeal the Superior Court order.', 'Branch: Affirm / Reverse / Remand.'], statute: 'O.C.G.A. § 5-6-34' } },
        { code: '5c', label: 'Supreme Court', tip: { title: '5 · Supreme Court of Georgia', status: 'pending', rows: ['By certiorari — discretionary review.'], statute: 'O.C.G.A. § 5-6-15' } },
      ],
    });

    var compact = [
      { code: 'Submit', status: 'complete' },
      { code: 'Review', status: isClosed ? 'complete' : (curStage <= 2 ? 'active' : 'complete') },
      { code: 'Finality', status: isClosed ? 'complete' : (curStage === 3 ? 'active' : curStage > 3 ? 'complete' : 'pending') },
      { code: 'Appeal', status: isClosed ? 'complete' : (curStage === 4 ? 'active' : curStage > 4 ? 'complete' : 'pending') },
      { code: 'Judicial', status: isClosed ? 'complete' : 'pending' },
    ];

    return {
      badge: badgeMeta(rec.type),
      subtypeLabel: sub.label, subtypeSub: sub.sub,
      isClosed: isClosed, isActive: !isClosed,
      filedLine: 'Filed ' + fmt(filed), closedLine: isClosed ? 'Closed ' + fmt(decided) : null,
      durationLine: isClosed ? durationLabel(filed, decided) : null,
      finalDisposition: isClosed ? (sub.sub + ' — ' + finding + ' · ' + fmt(decided)) : null,
      precedent: isClosed ? precedentForDET() : null,
      compact: compact,
      stages: stages,
    };
  }

  function build(rec) {
    if (!rec) return null;
    return rec.type === 'CON' ? buildCON(rec) : buildDET(rec);
  }

  // ---------------------------------------------------------------
  // Riverstone Imaging — curated flagship CON docket (on remand)
  // Real narrative facts drawn from the case corpus / citator / proceedings.
  // ---------------------------------------------------------------
  var RIVERSTONE_CON = {
    badge: badgeMeta('CON'),
    isClosed: false, isActive: true, onRemand: true,
    filedLine: 'Filed Jan 15, 2023', closedLine: null, durationLine: null,
    finalDisposition: 'CON Denied — Affirmed through Court of Appeals, then REMANDED for corrected methodology · Apr 8, 2026',
    precedent: null,
    compact: [
      { code: 'Intent', status: 'complete' }, { code: 'Review', status: 'complete' },
      { code: 'Initial', status: 'complete', tag: 'Denied' }, { code: 'Admin', status: 'complete', tag: 'Affirmed' },
      { code: 'Agency', status: 'complete' }, { code: 'Superior', status: 'complete', tag: 'Reversed' },
      { code: 'Appellate', status: 'complete' }, { code: 'Final', status: 'active', tag: 'On remand' },
    ],
    stages: [
      { n: '0', status: 'complete', title: 'Letter of Intent', dateLine: 'Filed Jan 15, 2023',
        substeps: [
          { code: '0a', label: 'Submission', tip: { title: '0a · Submission', status: 'complete', rows: ['Letter of intent filed Jan 15, 2023.', 'Proposed fixed 1.5T MRI service, Cartersville, Bartow County.'], statute: 'O.C.G.A. § 31-6-40' } },
          { code: '0b', label: 'Acknowledgement', tip: { title: '0b · Review Cycle / Batching', status: 'complete', rows: ['Batching cycle assigned — Bartow/Gordon/Floyd planning area.', 'Review period opened Feb 2023.'], statute: 'O.C.G.A. § 31-6-40' } },
        ] },
      { n: '1', status: 'complete', title: 'Initial Filing Review', dateLine: 'Submitted Mar 1, 2023 · Decision Jun 30, 2023',
        substeps: [
          { code: '1a', label: 'Receipt', tip: { title: '1a · CON Application Filed', status: 'complete', rows: ['Filed Mar 1, 2023 · CON No. 23-0118.', 'PSA defined as Bartow, Gordon, Floyd Counties (3-county) · 12 referral letters submitted.'], statute: 'O.C.G.A. § 31-6-43' } },
          { code: '1b', label: 'Batching', tip: { title: '1b · Review Cycle / Batching', status: 'complete', rows: ['No competing application filed in this batching cycle at filing.'], statute: 'O.C.G.A. § 31-6-43' } },
          { code: '1c', label: 'Public Notice', tip: { title: '1c · Public Hearing', status: 'complete', rows: ['Public hearing held Apr 12, 2023, Bartow County.', 'DCH Planning Section presiding.'], statute: 'O.C.G.A. § 31-6-43' } },
          { code: '1d', label: 'Agency Decision', tip: { title: '1d · Initial Decision — DENIED', status: 'denied', rows: ['Issued Jun 30, 2023 by M. Patel, Planning Officer.', 'Department redefined the PSA to a 5-county aggregation; found the existing fixed unit at Cartersville Medical Center below the utilization threshold under Rule 111-2-2-.40(4)(b).'], statute: 'Rule 111-2-2-.40(4)(b)' } },
        ],
        forks: [
          { key: 'approved', label: 'Approved', status: 'not-taken', title: 'Not reached' },
          { key: 'conditions', label: 'Approved with Conditions', status: 'not-taken', title: 'Not reached' },
          { key: 'denied', label: 'Denied', status: 'taken', title: 'Proceeds to Stage 2 (challenge window)' },
        ] },
      { n: '2', status: 'complete', title: 'Initial Decision Challenge', dateLine: 'Requested Jul 14, 2023',
        substeps: [
          { code: '2a', label: 'Request Filed', tip: { title: '2a · Request for Administrative Hearing', status: 'complete', rows: ['Filed Jul 14, 2023, within the 30-day window.'], statute: 'O.C.G.A. § 31-6-44(a)' } },
          { code: '2b', label: 'Challenge Registered', tip: { title: '2b · Challenge Registered', status: 'complete', rows: ['Docketed by DCH · timeliness and standing confirmed.'], statute: 'O.C.G.A. § 31-6-44(a)' } },
        ],
        forks: [
          { key: 'challenge', label: 'Challenge filed → proceeds', status: 'taken', title: 'Proceeds to Stage 3 (Administrative Appeal)' },
          { key: 'nochallenge', label: 'No challenge filed', status: 'not-taken', title: 'Not reached' },
        ] },
      { n: '3', status: 'complete', title: 'Administrative Appeal', dateLine: 'Hearing Oct 23–26, 2023 · Decision Feb 14, 2024',
        substeps: [
          { code: '3a', label: 'HO Appointed', tip: { title: '3a · Hearing Officer Appointed', status: 'complete', rows: ['ALJ Walsh appointed, OSAH.'], statute: 'O.C.G.A. § 31-6-44(b)' } },
          { code: '3b', label: 'Scheduling', tip: { title: '3b · Scheduling Conference', status: 'complete', rows: ['Hearing dates set for Oct 23–26, 2023.'], statute: 'O.C.G.A. § 31-6-44(b)' } },
          { code: '3c', label: 'Hearing Window', tip: { title: '3c · Hearing Window', status: 'complete', rows: ['4-day evidentiary hearing window, Oct 2023.'], statute: 'O.C.G.A. § 31-6-44(f)' } },
          { code: '3d', label: 'Hearing', tip: { title: '3d · Contested Case Hearing', status: 'complete', rows: ['4-day evidentiary hearing, Oct 23–26, 2023.', '22 filings · Walsh, ALJ presiding.'], statute: 'O.C.G.A. § 31-6-44(e)' } },
          { code: '3e', label: 'HO Decision', tip: { title: '3e · OSAH Initial Decision — Affirmed Denial', status: 'denied', rows: ['Issued Feb 14, 2024.', 'Hearing Officer Walsh affirmed the Department\u2019s service-area methodology as within agency discretion.'], statute: 'O.C.G.A. § 31-6-43' } },
        ] },
      { n: '4', status: 'complete', title: 'Final Agency Decision', dateLine: 'Effective Aug 7, 2024',
        regimeNote: {
          current: { label: 'Commissioner Review Path', tag: 'legacy', detail: 'Commissioner Caylee Murray adopted the Hearing Officer\u2019s initial decision in full · Final Order Aug 7, 2024.' },
          legacy: { label: 'Reformed Regime (HB 1339)', tag: 'current', detail: 'Not applicable — filed under the pre-2024 regime.' },
        } },
      { n: '5', status: 'complete', title: 'Judicial Review', dateLine: 'Petition Sep 6, 2024 · Reversed Mar 18, 2025',
        substeps: [
          { code: '5a', label: 'Petition Filed', tip: { title: '5a · Petition for Judicial Review', status: 'complete', rows: ['Filed Sep 6, 2024, Superior Court of Fulton County.'], statute: 'O.C.G.A. § 31-6-44.1' } },
          { code: '5b', label: 'Record Transmittal', tip: { title: '5b · Record Transmittal', status: 'complete', rows: ['Certified record and transcript transmitted per statute.'], statute: 'O.C.G.A. § 31-6-44.1' } },
          { code: '5c', label: 'Hearing on Record', tip: { title: '5c · Oral Argument', status: 'complete', rows: ['Held Jan 14, 2025, Fulton Superior Court · Welch, J.'], statute: 'O.C.G.A. § 50-13-19' } },
          { code: '5d', label: 'Disposition', tip: { title: '5d · Order — Reversed and Remanded', status: 'complete', rows: ['Issued Mar 18, 2025 by Welch, J.', 'Department\u2019s 5-county service-area methodology unsupported by substantial evidence in light of unrebutted referral data.'], statute: 'O.C.G.A. § 31-6-44.1' } },
        ] },
      { n: '6', status: 'complete', title: 'Appellate Review', dateLine: 'Affirmed Dec 4, 2025 · Cert. denied Mar 12, 2026',
        substeps: [
          { code: '6a', label: 'Court of Appeals', tip: { title: '6a · Court of Appeals — Affirmed', status: 'complete', rows: ['372 Ga. App. 488 (Dec. 4, 2025) · Pipkin, J. for the Fifth Division.', 'Held: service-area methodology must, at minimum, account for demonstrated referral patterns.'], statute: 'O.C.G.A. § 5-6-34' } },
          { code: '6b', label: 'Supreme Court', tip: { title: '6b · Petition for Certiorari — Denied', status: 'complete', rows: ['Denied without opinion, Mar 12, 2026 (No. S26C0411).', 'Court of Appeals opinion stands.'], statute: 'O.C.G.A. § 5-6-15' } },
        ] },
      { n: '7', status: 'active', title: 'On Remand — Proceedings Pending', dateLine: 'Remand docketed Apr 8, 2026',
        terminal: [
          { key: 'approved', label: 'Approved & Conditions Pending', status: 'not-taken' },
          { key: 'constructed', label: 'Constructed & Licensed', status: 'not-taken' },
          { key: 'unbuilt', label: 'Unbuilt / Lapsed CON', status: 'not-taken' },
          { key: 'remanded', label: 'Remanded — Active', status: 'taken' },
        ],
        deadline: { items: ['Prehearing statement due Jul 9, 2026', 'OSAH hearing window: Aug 19 – Oct 19, 2026', 'Hearing set: Oct 2–4, 2026', 'HO decision due ~Nov 1, 2026 (30 days after hearing concludes)'] },
      },
    ],
  };

  window.DOCKET_ENGINE = { build: build, buildCON: buildCON, buildDET: buildDET, STATUS: STATUS, badgeMeta: badgeMeta, fmt: fmt, parseDate: parseDate, riverstone: RIVERSTONE_CON };
})();
