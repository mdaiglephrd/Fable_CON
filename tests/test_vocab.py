from common import vocab


def test_county_count_exact():
    assert len(vocab.COUNTIES) == 159
    assert len(set(vocab.COUNTIES)) == 159


def test_vocab_sizes():
    assert len(vocab.SERVICE_TYPES) == 26
    assert len(vocab.MATTER_TYPES) == 5
    assert len(vocab.ACTION_TYPES) == 8
    assert len(vocab.DOC_TYPES) == 14
    assert len(vocab.PHASES) == 5
    assert len(vocab.OUTCOMES) == 13
    assert len(vocab.DECISION_LEVELS) == 5
    assert len(vocab.VALIDATION_STATUSES) == 4
    assert len(vocab.REPORT_SECTIONS) == 15


def test_match_county():
    assert vocab.match_county("Fulton") == "Fulton"
    assert vocab.match_county("FULTON") == "Fulton"
    assert vocab.match_county("fulton county") == "Fulton"
    assert vocab.match_county("DeKalb") == "DeKalb"
    assert vocab.match_county("DE KALB") == "DeKalb"
    assert vocab.match_county("Ben-Hill") == "Ben Hill"
    assert vocab.match_county("McDuffie") == "McDuffie"
    assert vocab.match_county("Springfield") is None
    assert vocab.match_county("") is None


def test_match_vocab_exact_and_dash_tolerant():
    assert vocab.match_vocab("approved", vocab.OUTCOMES) == "Approved"
    assert (
        vocab.match_vocab("Judicial Review - Superior Court", vocab.PHASES)
        == "Judicial Review – Superior Court"
    )
    assert (
        vocab.match_vocab("ambulatory surgery - multi-specialty", vocab.SERVICE_TYPES)
        == "Ambulatory surgery — multi-specialty"
    )
    assert vocab.match_vocab("Totally Made Up", vocab.OUTCOMES) is None
    assert vocab.match_vocab("", vocab.OUTCOMES) is None
