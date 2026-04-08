from app.services.query_classifier import classify_query


def test_document_about_is_global():
    assert classify_query("what is the document about?") == "global"


def test_specific_phase_question_is_local():
    assert classify_query("what is the Phase 1") == "local"


def test_ordinal_phase_question_is_local():
    assert classify_query("what is the second phase") == "local"


def test_summary_keyword_is_global():
    assert classify_query("give me a summary") == "global"


def test_specific_section_question_is_local():
    assert classify_query("explain section 2 in detail") == "local"


def test_model_training_purpose_question_is_global():
    assert classify_query("for what is the model being trained here?") == "global"
