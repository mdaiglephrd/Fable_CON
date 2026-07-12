/*
 * Controlled vocabularies for the research console — mirrors common/vocab.py
 * (the codes stored in the database are these exact strings). Keep in sync by
 * hand; the Python module is the source of truth.
 */

/** con.vocab_docket_family — docket family classification. */
export const DOCKET_FAMILIES = [
  'CON',
  'DET',
  'DET-EQT',
  'DET-ASC',
  'LNR-EQT',
  'LNR-ASC',
] as const;

export const DOC_TYPES = [
  'Application/Request',
  'Decision/Determination',
  'Hearing Officer Decision',
  'Final Agency Decision',
  'Order',
  'Notice',
  'Transcript',
  'Exhibit',
  'Brief/Memorandum',
  'Correspondence',
  'HFR Opinion',
  'Court Order/Opinion',
  'Settlement/Withdrawal',
  'Other',
] as const;

export const PHASES = [
  'Initial Application',
  'Administrative Appeal',
  'Judicial Review – Superior Court',
  'Judicial Review – Court of Appeals',
  'Judicial Review – Supreme Court of GA',
] as const;

export const OUTCOMES = [
  'Approved',
  'Approved with conditions',
  'Partially approved',
  'Denied',
  'Withdrawn',
  'Dismissed',
  'Remanded',
  'Settled',
  'Affirmed (appeal)',
  'Reversed (appeal)',
  'Vacated (appeal)',
  'Pending',
  'Unknown',
] as const;

export const DECISION_LEVELS: { level: number; label: string }[] = [
  { level: 1, label: 'Desk Decision' },
  { level: 2, label: 'Hearing Officer Decision' },
  { level: 3, label: 'Superior Court Decision' },
  { level: 4, label: 'Appellate Court Decision' },
  { level: 5, label: 'Initial Application' },
];

/** con.vocab_event_type — docket_event timeline event types. */
export const EVENT_TYPES = ['Filing', 'Order', 'Opinion', 'Hearing', 'Brief', 'Notice'] as const;

/** Weekly-report lifecycle section codes with display labels. */
export const REPORT_SECTION_LABELS: Record<string, string> = {
  LETTER_OF_INTENT: 'Letters of intent',
  LOI_EXPIRED: 'Expired letters of intent',
  NEW_APPLICATION: 'New applications',
  WITHDRAWN_APPLICATION: 'Withdrawn applications',
  PENDING_APPLICATION: 'Pending applications',
  APPROVED: 'Approved',
  DENIED: 'Denied',
  DISQUALIFIED: 'Disqualified',
  APPEALED: 'Appealed',
  APPEALED_DETERMINATION: 'Appealed determinations',
  LETTER_OF_DETERMINATION: 'Letters of determination',
  DET_REVIEW: 'Determination reviews',
  LNR_CONVERSION: 'LNR conversions',
  EXTENDED_IMPLEMENTATION: 'Extended implementation',
  OTHER: 'Other',
};

/** The 159 Georgia counties, Title Case as conventionally written. */
export const COUNTIES: string[] = [
  'Appling', 'Atkinson', 'Bacon', 'Baker', 'Baldwin', 'Banks', 'Barrow', 'Bartow',
  'Ben Hill', 'Berrien', 'Bibb', 'Bleckley', 'Brantley', 'Brooks', 'Bryan', 'Bulloch',
  'Burke', 'Butts', 'Calhoun', 'Camden', 'Candler', 'Carroll', 'Catoosa', 'Charlton',
  'Chatham', 'Chattahoochee', 'Chattooga', 'Cherokee', 'Clarke', 'Clay', 'Clayton',
  'Clinch', 'Cobb', 'Coffee', 'Colquitt', 'Columbia', 'Cook', 'Coweta', 'Crawford',
  'Crisp', 'Dade', 'Dawson', 'Decatur', 'DeKalb', 'Dodge', 'Dooly', 'Dougherty',
  'Douglas', 'Early', 'Echols', 'Effingham', 'Elbert', 'Emanuel', 'Evans', 'Fannin',
  'Fayette', 'Floyd', 'Forsyth', 'Franklin', 'Fulton', 'Gilmer', 'Glascock', 'Glynn',
  'Gordon', 'Grady', 'Greene', 'Gwinnett', 'Habersham', 'Hall', 'Hancock', 'Haralson',
  'Harris', 'Hart', 'Heard', 'Henry', 'Houston', 'Irwin', 'Jackson', 'Jasper',
  'Jeff Davis', 'Jefferson', 'Jenkins', 'Johnson', 'Jones', 'Lamar', 'Lanier',
  'Laurens', 'Lee', 'Liberty', 'Lincoln', 'Long', 'Lowndes', 'Lumpkin', 'Macon',
  'Madison', 'Marion', 'McDuffie', 'McIntosh', 'Meriwether', 'Miller', 'Mitchell',
  'Monroe', 'Montgomery', 'Morgan', 'Murray', 'Muscogee', 'Newton', 'Oconee',
  'Oglethorpe', 'Paulding', 'Peach', 'Pickens', 'Pierce', 'Pike', 'Polk', 'Pulaski',
  'Putnam', 'Quitman', 'Rabun', 'Randolph', 'Richmond', 'Rockdale', 'Schley',
  'Screven', 'Seminole', 'Spalding', 'Stephens', 'Stewart', 'Sumter', 'Talbot',
  'Taliaferro', 'Tattnall', 'Taylor', 'Telfair', 'Terrell', 'Thomas', 'Tift',
  'Toombs', 'Towns', 'Treutlen', 'Troup', 'Turner', 'Twiggs', 'Union', 'Upson',
  'Walker', 'Walton', 'Ware', 'Warren', 'Washington', 'Wayne', 'Webster', 'Wheeler',
  'White', 'Whitfield', 'Wilcox', 'Wilkes', 'Wilkinson', 'Worth',
];
