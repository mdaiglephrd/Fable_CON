-- 0001_schema_and_vocab.sql
-- Schema `con`, vocabulary tables, and vocabulary seed data.
-- Seed values are generated from common/vocab.py and must stay byte-identical
-- to those constants (DESIGN.md: codes are the exact human-readable strings).
-- migrate.py guarantees run-once, so seeds are plain INSERTs.

IF SCHEMA_ID(N'con') IS NULL
    EXEC (N'CREATE SCHEMA con');
GO

CREATE TABLE con.vocab_service_type (
    code NVARCHAR(100) NOT NULL,
    CONSTRAINT PK_vocab_service_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_matter_type (
    code NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_vocab_matter_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_action_type (
    code NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_vocab_action_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_doc_type (
    code NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_vocab_doc_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_phase (
    code NVARCHAR(80) NOT NULL,
    CONSTRAINT PK_vocab_phase PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_outcome (
    code NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_vocab_outcome PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_decision_level (
    [level] TINYINT NOT NULL,
    label   NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_vocab_decision_level PRIMARY KEY ([level])
);
GO

CREATE TABLE con.county (
    name NVARCHAR(30) NOT NULL,
    CONSTRAINT PK_county PRIMARY KEY (name)
);
GO

-- 26 service types (common/vocab.py SERVICE_TYPES)
INSERT INTO con.vocab_service_type (code)
VALUES
    (N'Acute-care/general hospital beds'),
    (N'Psychiatric inpatient beds'),
    (N'Substance-abuse beds'),
    (N'Skilled nursing/LTC beds'),
    (N'Comprehensive inpatient rehabilitation beds'),
    (N'Ambulatory surgery — single-specialty'),
    (N'Ambulatory surgery — multi-specialty'),
    (N'Open-heart/cardiac surgery'),
    (N'Cardiac catheterization'),
    (N'Megavoltage radiation therapy'),
    (N'PET'),
    (N'MRI'),
    (N'CT'),
    (N'Other diagnostic imaging'),
    (N'Obstetrical services'),
    (N'NICU/perinatal'),
    (N'Organ transplant'),
    (N'Lithotripsy'),
    (N'Renal dialysis/ESRD'),
    (N'Home health'),
    (N'Hospice/palliative'),
    (N'New/replacement hospital'),
    (N'Freestanding ED'),
    (N'Birthing center'),
    (N'Major medical equipment'),
    (N'Capital expenditure / new institutional health service (catch-all)');

GO

-- 5 matter types (MATTER_TYPES)
INSERT INTO con.vocab_matter_type (code)
VALUES
    (N'CON Application'),
    (N'Determination/Reviewability (DET)'),
    (N'Administrative Appeal'),
    (N'Judicial Review'),
    (N'Other/Administrative');

GO

-- 8 action types (ACTION_TYPES)
INSERT INTO con.vocab_action_type (code)
VALUES
    (N'New service/facility'),
    (N'Bed or capacity addition'),
    (N'Relocation'),
    (N'Replacement'),
    (N'Change of ownership (CHOW)'),
    (N'Cost overrun/capital amendment'),
    (N'Determination request'),
    (N'Other');

GO

-- 14 document types (DOC_TYPES)
INSERT INTO con.vocab_doc_type (code)
VALUES
    (N'Application/Request'),
    (N'Decision/Determination'),
    (N'Hearing Officer Decision'),
    (N'Final Agency Decision'),
    (N'Order'),
    (N'Notice'),
    (N'Transcript'),
    (N'Exhibit'),
    (N'Brief/Memorandum'),
    (N'Correspondence'),
    (N'HFR Opinion'),
    (N'Court Order/Opinion'),
    (N'Settlement/Withdrawal'),
    (N'Other');

GO

-- 5 phases (PHASES)
INSERT INTO con.vocab_phase (code)
VALUES
    (N'Initial Application'),
    (N'Administrative Appeal'),
    (N'Judicial Review – Superior Court'),
    (N'Judicial Review – Court of Appeals'),
    (N'Judicial Review – Supreme Court of GA');

GO

-- 13 outcomes (OUTCOMES)
INSERT INTO con.vocab_outcome (code)
VALUES
    (N'Approved'),
    (N'Approved with conditions'),
    (N'Partially approved'),
    (N'Denied'),
    (N'Withdrawn'),
    (N'Dismissed'),
    (N'Remanded'),
    (N'Settled'),
    (N'Affirmed (appeal)'),
    (N'Reversed (appeal)'),
    (N'Vacated (appeal)'),
    (N'Pending'),
    (N'Unknown');

GO

-- 5 decision levels (DECISION_LEVELS)
INSERT INTO con.vocab_decision_level ([level], label)
VALUES
    (1, N'Desk Decision'),
    (2, N'Hearing Officer Decision'),
    (3, N'Superior Court Decision'),
    (4, N'Appellate Court Decision'),
    (5, N'Initial Application');

GO

-- The 159 Georgia counties, Title Case (COUNTIES)
INSERT INTO con.county (name)
VALUES
    (N'Appling'),
    (N'Atkinson'),
    (N'Bacon'),
    (N'Baker'),
    (N'Baldwin'),
    (N'Banks'),
    (N'Barrow'),
    (N'Bartow'),
    (N'Ben Hill'),
    (N'Berrien'),
    (N'Bibb'),
    (N'Bleckley'),
    (N'Brantley'),
    (N'Brooks'),
    (N'Bryan'),
    (N'Bulloch'),
    (N'Burke'),
    (N'Butts'),
    (N'Calhoun'),
    (N'Camden'),
    (N'Candler'),
    (N'Carroll'),
    (N'Catoosa'),
    (N'Charlton'),
    (N'Chatham'),
    (N'Chattahoochee'),
    (N'Chattooga'),
    (N'Cherokee'),
    (N'Clarke'),
    (N'Clay'),
    (N'Clayton'),
    (N'Clinch'),
    (N'Cobb'),
    (N'Coffee'),
    (N'Colquitt'),
    (N'Columbia'),
    (N'Cook'),
    (N'Coweta'),
    (N'Crawford'),
    (N'Crisp'),
    (N'Dade'),
    (N'Dawson'),
    (N'Decatur'),
    (N'DeKalb'),
    (N'Dodge'),
    (N'Dooly'),
    (N'Dougherty'),
    (N'Douglas'),
    (N'Early'),
    (N'Echols'),
    (N'Effingham'),
    (N'Elbert'),
    (N'Emanuel'),
    (N'Evans'),
    (N'Fannin'),
    (N'Fayette'),
    (N'Floyd'),
    (N'Forsyth'),
    (N'Franklin'),
    (N'Fulton'),
    (N'Gilmer'),
    (N'Glascock'),
    (N'Glynn'),
    (N'Gordon'),
    (N'Grady'),
    (N'Greene'),
    (N'Gwinnett'),
    (N'Habersham'),
    (N'Hall'),
    (N'Hancock'),
    (N'Haralson'),
    (N'Harris'),
    (N'Hart'),
    (N'Heard'),
    (N'Henry'),
    (N'Houston'),
    (N'Irwin'),
    (N'Jackson'),
    (N'Jasper'),
    (N'Jeff Davis'),
    (N'Jefferson'),
    (N'Jenkins'),
    (N'Johnson'),
    (N'Jones'),
    (N'Lamar'),
    (N'Lanier'),
    (N'Laurens'),
    (N'Lee'),
    (N'Liberty'),
    (N'Lincoln'),
    (N'Long'),
    (N'Lowndes'),
    (N'Lumpkin'),
    (N'Macon'),
    (N'Madison'),
    (N'Marion'),
    (N'McDuffie'),
    (N'McIntosh'),
    (N'Meriwether'),
    (N'Miller'),
    (N'Mitchell'),
    (N'Monroe'),
    (N'Montgomery'),
    (N'Morgan'),
    (N'Murray'),
    (N'Muscogee'),
    (N'Newton'),
    (N'Oconee'),
    (N'Oglethorpe'),
    (N'Paulding'),
    (N'Peach'),
    (N'Pickens'),
    (N'Pierce'),
    (N'Pike'),
    (N'Polk'),
    (N'Pulaski'),
    (N'Putnam'),
    (N'Quitman'),
    (N'Rabun'),
    (N'Randolph'),
    (N'Richmond'),
    (N'Rockdale'),
    (N'Schley'),
    (N'Screven'),
    (N'Seminole'),
    (N'Spalding'),
    (N'Stephens'),
    (N'Stewart'),
    (N'Sumter'),
    (N'Talbot'),
    (N'Taliaferro'),
    (N'Tattnall'),
    (N'Taylor'),
    (N'Telfair'),
    (N'Terrell'),
    (N'Thomas'),
    (N'Tift'),
    (N'Toombs'),
    (N'Towns'),
    (N'Treutlen'),
    (N'Troup'),
    (N'Turner'),
    (N'Twiggs'),
    (N'Union'),
    (N'Upson'),
    (N'Walker'),
    (N'Walton'),
    (N'Ware'),
    (N'Warren'),
    (N'Washington'),
    (N'Wayne'),
    (N'Webster'),
    (N'Wheeler'),
    (N'White'),
    (N'Whitfield'),
    (N'Wilcox'),
    (N'Wilkes'),
    (N'Wilkinson'),
    (N'Worth');

GO
