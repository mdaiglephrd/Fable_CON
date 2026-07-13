-- 0010_axis_vocab.sql
-- Georgia CON Tagging Taxonomy vocab: Axis 1 (proceeding type), Axis 2 (authority type,
-- incl. Masterfile), Axis 3 (substantive issue, 100-900 series), Axis 4 (procedural issue,
-- P100-P900 series). Seeded verbatim from GeorgiaCONTaggingTaxonomy_2.docx; codes mirrored
-- in common/axis_taxonomy.py.

CREATE TABLE con.vocab_axis1_proceeding_type (
    code        NVARCHAR(20)  NOT NULL,
    description NVARCHAR(400) NULL,
    CONSTRAINT PK_vocab_axis1_proceeding_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.vocab_axis2_authority_type (
    code        NVARCHAR(60)  NOT NULL,
    description NVARCHAR(400) NULL,
    CONSTRAINT PK_vocab_axis2_authority_type PRIMARY KEY (code)
);
GO

CREATE TABLE con.axis3_substantive_issue (
    code        NVARCHAR(10)  NOT NULL,
    parent_code NVARCHAR(10)  NULL,
    label       NVARCHAR(600) NOT NULL,
    citation    NVARCHAR(1000) NULL,
    sort_order  INT           NOT NULL,
    CONSTRAINT PK_axis3_substantive_issue PRIMARY KEY (code),
    CONSTRAINT FK_axis3_substantive_issue_parent
        FOREIGN KEY (parent_code) REFERENCES con.axis3_substantive_issue (code)
);
GO

CREATE TABLE con.axis4_procedural_issue (
    code        NVARCHAR(10)  NOT NULL,
    parent_code NVARCHAR(10)  NULL,
    label       NVARCHAR(600) NOT NULL,
    citation    NVARCHAR(1000) NULL,
    sort_order  INT           NOT NULL,
    CONSTRAINT PK_axis4_procedural_issue PRIMARY KEY (code),
    CONSTRAINT FK_axis4_procedural_issue_parent
        FOREIGN KEY (parent_code) REFERENCES con.axis4_procedural_issue (code)
);
GO

-- Axis 1 seed
INSERT INTO con.vocab_axis1_proceeding_type (code, description) VALUES (N'CON', N'Includes Letters of Intent (LOIs).');
INSERT INTO con.vocab_axis1_proceeding_type (code, description) VALUES (N'DET', NULL);
INSERT INTO con.vocab_axis1_proceeding_type (code, description) VALUES (N'DET-ASC', N'Includes LNR-ASC filings prior to 2019.');
INSERT INTO con.vocab_axis1_proceeding_type (code, description) VALUES (N'DET-EQT', N'Includes LNR-EQT filings prior to 2019.');
INSERT INTO con.vocab_axis1_proceeding_type (code, description) VALUES (N'Other', N'Rare escape hatch; use sparingly, not as a default.');
GO

-- Axis 2 seed
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Statute', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Rule', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'DCH Desk Decision', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'CON Appeals Panel Decision', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'OSAH ALJ Decision', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'DCH Commissioner Final Order', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Superior Court Opinion', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'GA Court of Appeals Opinion', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'GA Supreme Court Opinion', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Application (non-authority)', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Additional Information (non-authority)', NULL);
INSERT INTO con.vocab_axis2_authority_type (code, description) VALUES (N'Masterfile', N'Selecting this value excludes every other Axis 2 value and suppresses Axis 3/4 tags for the document.');
GO

-- con.axis3_substantive_issue seed (125 rows) -- parents inserted before children (document order).
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'100', NULL, N'Reviewability & Jurisdiction', NULL, 0);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'110', N'100', N'New/expanded/relocated facility construction', N'§ 31-6-40(a)(1)', 1);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'111', N'100', N'Equipment purchase or lease trigger', N'§ 31-6-40(a)(3)', 2);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'112', N'100', N'Bed capacity increase trigger', N'§ 31-6-40(a)(4)', 3);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'113', N'100', N'New clinical health service / "12-month rule"', N'§ 31-6-40(a)(5)', 4);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'114', N'100', N'Conversion or upgrade to specialty hospital / facility-type conversion', N'§ 31-6-40(a)(6)', 5);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'115', N'100', N'New service at a diagnostic/treatment/rehab center (radiation therapy, biliary lithotripsy, OR surgery, cardiac cath)', N'§ 31-6-40(a)(7)', 6);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'116', N'100', N'Destination cancer hospital ↔ general cancer hospital conversion', N'§ 31-6-40(a)(8), § 31-6-40.3', 7);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'117', N'100', N'Redistribution of already-licensed beds (not a reviewable event)', N'Premier Health Care Invs. v. UHS of Anchor, 310 Ga. 32 (2020)', 8);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'118', N'100', N'Relocation of an existing facility/service', N'§ 31-6-47(a)(24); HCA Health Servs. v. Roach, 263 Ga. 798 (1994); North Fulton Med. Ctr. v. Stephenson, 269 Ga. 540 (1998)', 9);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'119', N'100', N'Grandfathered / pre-program status', N'HCA Health Servs. v. Roach, 263 Ga. 798 (1994)', 10);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'120', N'100', N'New and emerging health care service / moratorium', N'§ 31-6-40(e)', 11);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'130', N'100', N'Facility/service definitional disputes', N'§ 31-6-2', 12);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'200', NULL, N'Exemptions & Non-Reviewability', NULL, 13);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'210', N'200', N'Government/institutional exemptions', N'§ 31-6-47(a)(1)–(5)', 14);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'220', N'200', N'Physician/dentist office exemption', N'§ 31-6-47(a)(4)', 15);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'230', N'200', N'Pre-application cost exemptions', N'§ 31-6-47(a)(6)–(8)', 16);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'240', N'200', N'Restructuring/acquisition exemption', N'§ 31-6-47(a)(9)', 17);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'250', N'200', N'Equipment acquisition/replacement/repair exemption', N'§ 31-6-47(a)(10), (28)', 18);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'260', N'200', N'Safety-hazard capital expenditure exemption', N'§ 31-6-47(a)(11)', 19);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'270', N'200', N'Cost-overrun exemption', N'§ 31-6-47(a)(12)', 20);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'280', N'200', N'Equipment transfer-between-facilities exemption', N'§ 31-6-47(a)(13)', 21);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'290', N'200', N'HMO-related exemption', N'§ 31-6-47(a)(14)', 22);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2A0', N'200', N'Bed capacity exemption (lesser of 10 beds/20% rule)', N'§ 31-6-47(a)(15)', 23);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2B0', N'200', N'Nonclinical project exemption', N'§ 31-6-47(a)(16)', 24);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2C0', N'200', N'Life plan community skilled-nursing exemption', N'§ 31-6-47(a)(17)', 25);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2D0', N'200', N'Single-specialty ASC exemption', N'§ 31-6-47(a)(18)', 26);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2E0', N'200', N'Joint-venture ASC exemption', N'§ 31-6-47(a)(19)', 27);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2F0', N'200', N'Imaging center population-needs-methodology exemption', N'§ 31-6-47(a)(20)', 28);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2G0', N'200', N'Cardiac catheterization exemptions (diagnostic/adult; C-PORT study)', N'§ 31-6-47(a)(21)–(22)', 29);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2H0', N'200', N'Correctional-facility infirmary exemption', N'§ 31-6-47(a)(23)', 30);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2I0', N'200', N'Relocation exemption (SNF/ICF/micro-hospital)', N'§ 31-6-47(a)(24)', 31);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2J0', N'200', N'Traumatic brain injury facility exemption', N'§ 31-6-47(a)(25)', 32);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2K0', N'200', N'Hospital remodel/renovate/replace capital exemption', N'§ 31-6-47(a)(26)', 33);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2L0', N'200', N'General renovation/refurbishment exemption', N'§ 31-6-47(a)(27)', 34);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2M0', N'200', N'Primary-campus capital expenditure exemption', N'§ 31-6-47(a)(29)', 35);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2N0', N'200', N'Letter-of-determination eligibility & scope', N'§ 31-6-47.1; r. 111-2-2-.10(1)(a)–(b), (2)', 36);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2O0', N'200', N'Exemption compliance conditions', N'indigent/charity care & Medicaid participation percentages — § 31-6-40(c)(2)', 37);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'2P0', N'200', N'Penalty/revocation for exemption noncompliance', N'§ 31-6-47.1(b)', 38);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'300', NULL, N'Application Eligibility', NULL, 39);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'310', N'300', N'Outstanding-obligations bar to new/modified CON', N'§ 31-6-42.1', 40);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'400', NULL, N'Review Standards & Criteria (the § 31-6-42(a) considerations)', NULL, 41);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'410', N'400', N'State health plan consistency', N'§ 31-6-42(a)(1)', 42);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'420', N'400', N'General/population need', N'§ 31-6-42(a)(2); Doctors Hosp. of Augusta v. DCH, 350 Ga. App. 36 (2019); Univ. Health Servs. v. Ga. DCH, 2026 Ga. App. LEXIS 139', 43);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'430', N'400', N'Existing/less-costly alternatives', N'§ 31-6-42(a)(3)', 44);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'440', N'400', N'Financial feasibility', N'§ 31-6-42(a)(4)', 45);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'450', N'400', N'Payor impact', N'§ 31-6-42(a)(5)', 46);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'460', N'400', N'Construction cost & energy-conservation reasonableness', N'§ 31-6-42(a)(6)', 47);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'470', N'400', N'Financial & physical accessibility', N'§ 31-6-42(a)(7)', 48);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'480', N'400', N'Positive relationship to / adverse impact on existing delivery system', N'§ 31-6-42(a)(8); Tanner Med. Ctr. v. Vest Newnan, 337 Ga. App. 884 (2016); Hospital Auth. v. State Health Planning Agency, 211 Ga. App. 407 (1993)', 49);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'490', N'400', N'Efficient utilization of proposing facility', N'§ 31-6-42(a)(9)', 50);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4A0', N'400', N'Out-of-service-area patient base', N'§ 31-6-42(a)(10)', 51);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4B0', N'400', N'Biomedical/behavioral research or national/regional service development', N'§ 31-6-42(a)(11)', 52);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4C0', N'400', N'Health professional training program needs', N'§ 31-6-42(a)(12)', 53);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4D0', N'400', N'Innovation, quality assurance, cost-effectiveness, competition', N'§ 31-6-42(a)(13)', 54);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4E0', N'400', N'HMO special needs', N'§ 31-6-42(a)(14)', 55);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4F0', N'400', N'Minimum quality standards / accreditation / volume thresholds', N'§ 31-6-42(a)(15)', 56);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4G0', N'400', N'Resource availability (staffing, management)', N'§ 31-6-42(a)(16)', 57);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4H0', N'400', N'Underrepresented health service preference', N'§ 31-6-42(a)(17)', 58);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4I0', N'400', N'Osteopathic medicine need determination', N'§ 31-6-42(b)', 59);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4J0', N'400', N'Destination cancer hospital-specific criteria', N'§ 31-6-42(b.1)', 60);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4K0', N'400', N'Sole-provider perinatal county exception', N'§ 31-6-42(b.2)', 61);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4L0', N'400', N'Minority-administered hospital extraordinary consideration', N'§ 31-6-42(c)', 62);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4M0', N'400', N'Atypical/geographic barrier exception', N'Kennestone Hosp. v. DCH, 346 Ga. App. 70 (2018); ASMC, LLC v. Northside Hosp., 344 Ga. App. 576 (2018); Ga. DCH v. Satilla Health Servs., 2004 Ga. App. LEXIS 376', 63);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4N0', N'400', N'Department''s obligation to specify applicable considerations & evidentiary support', N'§ 31-6-42(e)', 64);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'4O0', N'400', N'Comparative batching priority factors as applied (which factor controlled the tie-break)', N'r. 111-2-2-.08(1)(h)', 65);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'500', NULL, N'Facility & Service-Specific Review Standards', NULL, 66);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'510', N'500', N'Short-stay general hospital beds', N'demand-based bed-need forecasting model; 50,000-person minimum target service area for a new hospital; trauma center / teaching hospital / sole community provider / critical access / hospital-closure exceptions to need and adverse-impact standards — r. 111-2-2-.20', 67);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'511', N'500', N'Adult cardiac catheterization', N'minimum 1,040 procedures/year service-area threshold; 100-procedure minimum performance standard — r. 111-2-2-.21', 68);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'512', N'500', N'Adult open heart surgery', N'minimum 300 procedures/year projected within 3 years; existing-service floor of 200 procedures/year; 250-procedure adult cath feeder-volume threshold — r. 111-2-2-.22', 69);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'513', N'500', N'Pediatric cardiac catheterization & open heart surgery', N'750 procedures/year per authorized service; 150 additional pediatric procedures/year within 3 years; 100-procedure pediatric cardiac surgery minimum — r. 111-2-2-.23', 70);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'514', N'500', N'Perinatal services / freestanding birthing centers', N'r. 111-2-2-.24 (see also 4K0 sole-provider exception)', 71);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'515', N'500', N'Psychiatric & substance abuse services', N'r. 111-2-2-.26. Repealed — see Appendix A. Flag any decision citing this as pre-repeal.', 72);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'520', N'500', N'Skilled nursing / intermediate care facilities', N'bed-need ratios (0.43 / 9.77 / 32.5 / 120.00 beds per 1,000 projected resident population by age cohort); minimum facility size thresholds (60 beds rural freestanding / 100 beds urban freestanding / 10 beds rural hospital-based / 20 beds urban hospital-based) — r. 111-2-2-.30', 73);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'521', N'500', N'Personal care homes', N'25-bed minimum; bed-need ratios (18.00 / 40.00 / 60.00 per 1,000 projected resident population) — r. 111-2-2-.31', 74);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'522', N'500', N'Home health services', N'geographic service area definition (contiguous-county grouping); unmet-need determination by service area; population-based need formula (4/5/45/185 patients per 1,000 by age cohort); 250/500-patient batching thresholds — r. 111-2-2-.32', 75);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'523', N'500', N'Life plan community (LPC) sheltered nursing facilities', N'modified initial-implementation duration rule — r. 111-2-2-.33', 76);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'524', N'500', N'Traumatic brain injury facilities', N'demand-based need methodology (2% transitional-living / 0.5% life-long-living demand factors); 85% occupancy standard; 6-bed minimum, 30-bed life-long-living cap — r. 111-2-2-.34', 77);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'525', N'500', N'Comprehensive inpatient physical rehabilitation', N'minimum 5-day/week multidisciplinary programming intensity; 85% capacity standard for bed-need projection; 20%-of-capacity/10-bed expansion exception at >60% occupancy; tiered minimum bed sizes; 50-mile/75,000-population exception — r. 111-2-2-.35', 78);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'526', N'500', N'Long-term care hospitals', N'occupancy-rate definition; short-stay-bed-to-LTCH conversion/reversion mechanics; official inventory effects; 1.3% demand factor with 6% rehab-overlap reduction, 85% capacity standard — r. 111-2-2-.36', 79);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'530', N'500', N'Ambulatory surgery centers', N'OR capacity standard (1,000 patients/OR/year, based on 250 OR-days × 4 procedures/day); need methodology combining hospital-dedicated and freestanding ASC OR counts — r. 111-2-2-.40', 80);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'531', N'500', N'PET units', N'optimal utilization defined as 2,750 scans/year — r. 111-2-2-.41', 81);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'532', N'500', N'Mega-voltage radiation therapy', N'separate standards for non-special-purpose vs. special-purpose MRT; 45-mile minimum distance from existing/approved unit; 150-patient/year minimum projected volume — r. 111-2-2-.42', 82);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'540', N'500', N'Destination / general cancer hospitals', N'§ 31-6-40.3, § 31-6-42(b.1)', 83);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'550', N'500', N'Freestanding emergency departments', N'Ga. DCH v. Houston Hosps., 365 Ga. App. 751 (2022); AU Med. Ctr. v. Ga. DCH, 366 Ga. App. 94 (2022)', 84);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'560', N'500', N'Rural health facilities / micro-hospitals', N'§ 31-6-2(23.2)', 85);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'600', NULL, N'Enforcement, Revocation & Penalties', NULL, 86);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'610', N'600', N'Revocation grounds (§ 31-6-45(a), elaborated at r. 111-2-2-.05(1)(a): false information, financial-obligation failure, implementation/performance-standard failure, unauthorized ownership transfer, unauthorized location change, condition noncompliance, late/incomplete reporting, unpaid fines, quality-standard failure, Medicaid-participation failure)', NULL, 87);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'620', N'600', N'Location-change protection against revocation', N'§ 31-6-45(a) proviso', 88);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'630', N'600', N'Untimely implementation revocation', N'§ 31-6-45(a.1); r. 111-2-2-.05(1)(f)', 89);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'640', N'600', N'Operating without a CON', N'license denial consequence — § 31-6-45(b); r. 111-2-2-.05(2)(a)', 90);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'650', N'600', N'Civil penalties for unauthorized operation', N'§ 31-6-45(c); r. 111-2-2-.05(2)(b)', 91);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'660', N'600', N'Injunctive relief & third-party standing to enforce', N'§ 31-6-45(d); r. 111-2-2-.05(2)(g); Diversified Health Mgt. Servs. v. Visiting Nurses Ass''n, 254 Ga. 500 (1985)', 92);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'670', N'600', N'Departmental investigations & records production', N'§ 31-6-45(e); r. 111-2-2-.05(3); Southeast Ga. Health Sys. v. Berry, 362 Ga. App. 422 (2022)', 93);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'680', N'600', N'Automatic revocation tied to license revocation', N'§ 31-6-45.1; r. 111-2-2-.05(1)(e)', 94);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'690', N'600', N'Medicaid participation condition & penalty for termination', N'§ 31-6-45.2; r. 111-2-2-.05(2)(d)', 95);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'6A0', N'600', N'Res judicata effects on reapplication', N'State Health Planning Agency v. Cribb Indus., 204 Ga. App. 285 (1992)', 96);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'6B0', N'600', N'Late-notification-of-acquisition penalty ($500/day)', N'r. 111-2-2-.05(2)(c)', 97);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'700', NULL, N'Appeal & Judicial Review — Standing, Merits Doctrine', NULL, 98);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'710', N'700', N'Standing/right to appeal a department decision (who qualifies, including the 30-day filing requirement as part of the doctrinal test)', N'§ 31-6-44(d); ProHealth Home Health-Ga. v. Ga. DCH, 377 Ga. App. 600 (2025); Loyd v. Ga. State Health Planning & Dev. Agency, 168 Ga. App. 850 (1983)', 99);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'720', N'700', N'Intervention', N'timeliness and requirements — § 31-6-44(d); r. 274-1-.03(2); Redmond Park Hosp. v. Floyd Health Care Mgmt., 360 Ga. App. 469 (2021)', 100);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'730', N'700', N'Substantial-justification / delay-or-harassment findings on the merits of an appeal', N'§ 31-6-44(f)(2)–(3); r. 274-1-.11(2)', 101);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'735', N'700', N'Commissioner-stage fee-shifting for appeals lacking substantial justification', N'historical only (r. 274-1-.13(6)–(7), (9), now repealed with no statutory replacement — § 31-6-44''s commissioner-review subsections were themselves deleted in 2024). Tag pre-July-2024 dockets only.', 102);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'740', N'700', N'New/additional evidence admissibility at hearing; new-need-study limitation', N'§ 31-6-44(g); r. 274-1-.10(9)–(11); Palmyra Park Hosp. v. Phoebe Sumter Med. Ctr., 310 Ga. App. 487 (2011)', 103);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'745', N'700', N'Scope of the appeal hearing', N'the § 31-6-44(f) issue-for-decision list as the operative boundary, plus § 31-6-47.1(a)''s separate routing of reviewability/determination disputes to the general GAPA track', 104);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'750', N'700', N'Ex parte contact', N'what constitutes prejudicial contact — § 31-6-44(h); North Fulton Cmty. Hosp. v. State Health Planning & Dev. Agency, 168 Ga. App. 801 (1983)', 105);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'760', N'700', N'"Competent substantial evidence" / deference standard applied to Commissioner review of hearing officer findings', N'historical only (see Appendix B). Tag pre-July-2024 CON Appeals Panel/Commissioner decisions: Vantage Cancer Ctrs. of Ga. v. Ga. DCH, 318 Ga. 361 (2024); Ga. DCH v. Houston Hosps., 372 Ga. App. 218 (2024); Northside Hosp. v. Northeast Ga. Med. Ctr., 373 Ga. App. 714 (2024)', 106);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'770', N'700', N'"Particularity" requirement for Commissioner departure from hearing officer findings', N'historical only, same basis as 760. Vantage Cancer Ctrs. of Ga. v. Ga. DCH, 318 Ga. 361 (2024)', 107);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'775', N'700', N'Judicial review standard', N'the six statutory grounds for reversal/modification, the "substantial evidence" standard''s express elevation above "any evidence" — § 31-6-44.1(a)', 108);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'780', N'700', N'CON Act vs. general APA', N'which procedural regime controls — Redmond Park Hosp. v. Floyd Health Care Mgmt., 360 Ga. App. 469 (2021)', 109);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'790', N'700', N'Exhaustion of administrative remedies (futility exception; "acting outside statutory authority" exception)', N'§ 50-13-19(a); Ga. DCH v. Ga. Soc''y of Ambulatory Surgery Ctrs., 290 Ga. 628 (2012); Ga. Soc''y of Ambulatory Surgery Ctrs. v. Ga. DCH, 316 Ga. App. 433 (2012)', 110);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'7A0', N'700', N'Venue', N'Tanner Med. Ctr. v. Vest Newnan, 337 Ga. App. 884 (2016)', 111);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'7B0', N'700', N'Agency as proper party respondent to judicial review', N'Loyd v. Ga. State Health Planning & Dev. Agency, 168 Ga. App. 850 (1983)', 112);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'7C0', N'700', N'Judicial deference to agency health-planning expertise', N'Ga. DCH v. Satilla Health Servs., 2004 Ga. App. LEXIS 376', 113);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'7D0', N'700', N'Superior Court fee-shifting for the prevailing party, including the "jurisdiction" carve-out''s meaning', N'fully live, self-sufficient statutory text — § 31-6-44.1(c); Lakeview Behavioral Health Sys. v. UHS Peachford, 321 Ga. App. 820 (2013); Tanner Med. Ctr. v. Vest Newnan, 344 Ga. App. 901 (2018)', 114);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'7E0', N'700', N'Deemed-affirmed-by-operation-of-law at the Superior Court stage (120/90/30-day mechanics)', N'§ 31-6-44.1(b); Kennestone Hosp. v. Cartersville Med. Ctr., 341 Ga. App. 28 (2017); Doctors Hosp. of Augusta v. DCH, 344 Ga. App. 583 (2018)', 115);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'800', NULL, N'Constitutional & Property-Rights Issues', NULL, 116);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'810', N'800', N'CON as a vested private property right', N'Kennestone Hosp. v. Emory Univ., 318 Ga. 169 (2024), rev''d 373 Ga. App. 114 (2024)', 117);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'820', N'800', N'Anti-Competitive Contracts Clause challenges', N'Women''s Surgical Ctr. v. Berry, 302 Ga. 349 (2017)', 118);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'830', N'800', N'Vagueness challenges to CON rules', N'Ga. DCH v. Northside Hosp., 295 Ga. 446 (2014)', 119);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'840', N'800', N'Legitimate legislative purpose / rational basis for CON program', N'Women''s Surgical Ctr. v. Berry, 302 Ga. 349 (2017)', 120);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'850', N'800', N'No vested right to operate a converted facility type', N'Emory Univ. v. Kennestone Hosp., 373 Ga. App. 114 (2024)', 121);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'900', NULL, N'Reporting & Transparency', NULL, 122);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'910', N'900', N'Facility annual reporting requirements', N'§ 31-6-70; r. 111-2-2-.04', 123);
INSERT INTO con.axis3_substantive_issue (code, parent_code, label, citation, sort_order) VALUES (N'920', N'900', N'DCH annual report to General Assembly / state health plan updates', N'§ 31-6-46', 124);
GO

-- con.axis4_procedural_issue seed (59 rows) -- parents inserted before children (document order).
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P100', NULL, N'Pre-Filing & Intent', NULL, 0);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P110', N'P100', N'Letter of intent', N'25-day pre-filing requirement — § 31-6-43(a)', 1);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P120', N'P100', N'Notice of intent to apply (batching-specific', N'25 calendar days from unmet-need publication) — r. 111-2-2-.08(1)(c)', 2);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P130', N'P100', N'Determination-request form requirements (one matter per request, $500 fee, fee waivers for hospital authorities/nonprofits)', N'r. 111-2-2-.10(1)', 3);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P200', NULL, N'Application Completeness & Amendment', NULL, 4);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P210', N'P200', N'Completeness determination & deficiency notice', N'§ 31-6-43(b); r. 111-2-2-.07(1)(a)', 5);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P220', N'P200', N'30-day applicant meeting / 45-day additional-information deadline', N'r. 111-2-2-.07(1)(f)', 6);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P230', N'P200', N'Amendment vs. new-application distinction (90-day amendment deadline; qualifying changes)', N'r. 111-2-2-.07(1)(f)–(g)', 7);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P240', N'P200', N'Withdrawal of application (including deemed-withdrawal on total scope/location/applicant change)', N'r. 111-2-2-.07(1)(g)', 8);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P300', NULL, N'Batching & Comparative Review Procedure', NULL, 9);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P310', N'P300', N'Unmet-need determination & batching cycle announcement (6-month review cycle)', N'r. 111-2-2-.08(1)(a)–(b)', 10);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P320', N'P300', N'Notice-of-intent-to-apply qualification & disqualification', N'r. 111-2-2-.08(1)(c)', 11);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P330', N'P300', N'Joinder procedure & 25-day joinder window', N'§ 31-6-43(f); r. 111-2-2-.07(1)(c), -.08(1)', 12);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P400', NULL, N'Opposition & Public Participation Mechanics', NULL, 13);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P410', N'P400', N'Notice of opposition form (30-day deadline; vendor-lobbyist certification requirement)', N'r. 111-2-2-.07(1)(h), -.08(1)(g)(4)', 14);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P420', N'P400', N'Opposition meeting logistics (no earlier than 60th day; one spokesperson; no applicant rebuttal)', N'§ 31-6-43(h); r. 111-2-2-.07(1)(h)(1)', 15);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P430', N'P400', N'Substantive opposition comment procedure', N'single-application rule & applicant response deadline (75th day) — r. 111-2-2-.07(1)(h)(2)–(3)', 16);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P440', N'P400', N'Public hearing request procedure (50-resident petition; 20-day request deadline; non-party testimony status)', N'r. 111-2-2-.07(1)(e)', 17);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P450', N'P400', N'Third-party/government notice obligations (newspaper, regional commission, county/municipal officials)', N'§ 31-6-43(b); r. 111-2-2-.07(1)(a)', 18);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P500', NULL, N'Review Timeline, Deadlines & Decision Content', NULL, 19);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P510', N'P500', N'Standard 120-day review clock', N'§ 31-6-43(d)(1); r. 111-2-2-.07(1)(b)', 20);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P520', N'P500', N'30-day extension to 150 days for good cause', N'§ 31-6-43(d)(1); r. 111-2-2-.07(1)(d)', 21);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P530', N'P500', N'Deemed-approved-by-default (121st/151st day)', N'§ 31-6-43(j); r. 111-2-2-.07(2)(f)', 22);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P540', N'P500', N'Emergency/expedited review (30-day cycle; telephone authorization; automatic approval on default)', N'§ 31-6-43(k); r. 111-2-2-.07(1)(i), (k)–(o)', 23);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P550', N'P500', N'Decision letter content requirements (findings per consideration; appeal-availability notice)', N'§ 31-6-43(i); r. 111-2-2-.07(2)(c)', 24);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P600', NULL, N'Determination (DET/LNR) Procedure', NULL, 25);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P610', N'P600', N'Determination request form, fee, and one-matter-per-request rule', N'r. 111-2-2-.10(1)', 26);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P620', N'P600', N'60-day determination review clock / 30-day extension to 90 days', N'§ 31-6-47.1(a); r. 111-2-2-.10(2)(c)', 27);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P630', N'P600', N'Non-precedential, fact-specific scope of determinations', N'r. 111-2-2-.10(1)(a)', 28);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P640', N'P600', N'Equipment determination', N'sworn affidavit & completion/interim reporting requirements (DET-EQT) — r. 111-2-2-.10(3)', 29);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P650', N'P600', N'ASC determination', N'ownership/utilization/specialty documentation requirements (DET-ASC) — r. 111-2-2-.10(4)', 30);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P660', N'P600', N'Notice of and opposition to determination requests', N'§ 31-6-47.1(a); r. 111-2-2-.10(2)(d)', 31);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P670', N'P600', N'Determination validity limits (non-transferable; invalidated by changed facts)', N'r. 111-2-2-.10(3)(f)', 32);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P700', NULL, N'Hearing Scheduling & Filing Mechanics (CON Appeal Panel)', NULL, 33);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P710', N'P700', N'Hearing/intervention request', N'30-day filing deadline; intervention request due within 10 days of the hearing request — § 31-6-44(d); r. 274-1-.03(2)', 34);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P715', N'P700', N'Appeal filing fee', N'$7,500 per party per application, rural-hospital-denial exemption, intervenor payment within 14 days — r. 274-1-.04', 35);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P720', N'P700', N'Hearing officer appointment & scheduling (60–120 day hearing window; 14-day scheduling conference and notice)', N'§ 31-6-44(d); r. 274-1-.06', 36);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P725', N'P700', N'Hearing location', N'r. 274-1-.08 (repealed; no statutory replacement identified — treat current status as uncertain)', 37);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P730', N'P700', N'De novo evidentiary hearing procedural framework under GAPA contested-case rules', N'§ 31-6-44(e); r. 274-1-.10(1)', 38);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P732', N'P700', N'Pre-hearing discovery mechanics (10-business-day discovery response; as-of-right discovery categories)', N'r. 274-1-.10(2)', 39);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P734', N'P700', N'Pre-hearing brief and written direct testimony requirements (8-page summary limit; expert witness written direct testimony in lieu of live direct)', N'r. 274-1-.10(3)–(6)', 40);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P736', N'P700', N'Order of proceeding & burden of proof allocation', N'r. 274-1-.10(7)–(8)', 41);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P740', N'P700', N'Remand procedure & deadline-setting', N'§ 31-6-44(g); r. 274-1-.11(7)', 42);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P750', N'P700', N'Findings of fact/conclusions of law', N'30-day post-hearing filing deadline (extendable up to 15 additional days for complexity) — § 31-6-44(i); r. 274-1-.11(1)', 43);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P755', N'P700', N'Optional Commissioner-designee review filing mechanics', N'30-day objection deadline; 61-day finality-by-default absent objection — r. 274-1-.12. Live and operative: the Appeals Panel serves as the Commissioner''s designee for this rule. The substantive review standard the designee applies is unconfirmed (see Appendix B).', 44);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P760', N'P700', N'Record maintenance & cost-sharing for hearing record preparation', N'r. 274-1-.19 (repealed; no statutory replacement identified — treat current status as uncertain)', 45);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P800', NULL, N'Post-Decision & Enforcement Procedure', NULL, 46);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P810', N'P800', N'Revocation notice & GAPA hearing procedure', N'§ 31-6-45(a); r. 111-2-2-.05(1)(a)–(b)', 47);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P820', N'P800', N'120-day reapplication bar after final revocation/denial', N'r. 111-2-2-.05(1)(c)', 48);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P830', N'P800', N'Voluntary revocation request (without prejudice)', N'r. 111-2-2-.05(1)(d)', 49);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P840', N'P800', N'Automatic revocation timing tied to license-revocation finality', N'§ 31-6-45.1; r. 111-2-2-.05(1)(e)', 50);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P850', N'P800', N'Fine assessment, notice, and 30/90-day payment deadlines', N'§ 31-6-45(c); r. 111-2-2-.05(2)(b), (f)', 51);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P860', N'P800', N'Department''s right to inspect/audit', N'r. 111-2-2-.05(3)', 52);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P870', N'P800', N'Progress/periodic reporting deadlines (180-day report rule)', N'§ 31-6-70; r. 111-2-2-.04, -.05(1)(f)(2)', 53);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P900', NULL, N'Judicial Review Mechanics', NULL, 54);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P910', N'P900', N'Judicial review filing procedure', N'§ 31-6-44.1(a)–(b)', 55);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P920', N'P900', N'Stay of CON effectiveness pending judicial review', N'r. 111-2-2-.07(2)(h)', 56);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P930', N'P900', N'Finality determination for appeal-clock purposes (when a decision becomes "final")', N'§ 31-6-44(j); r. 111-2-2-.05(1)(c)', 57);
INSERT INTO con.axis4_procedural_issue (code, parent_code, label, citation, sort_order) VALUES (N'P940', N'P900', N'Record transmission deadline (30 days) & Superior Court hearing/decision timing (120-day deemed-affirmed rule)', N'§ 31-6-44.1(b)', 58);
GO

