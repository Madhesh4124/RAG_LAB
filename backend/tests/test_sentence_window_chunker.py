from app.services.chunking.sentence_window import SentenceWindowChunker


def test_sentence_window_prefixes_bullets_with_section_heading():
    text = (
        "Text Preprocessing\n"
        "- Lowercasing, punctuation removal, whitespace normalization\n"
        "- Stemming (Porter, Snowball) -- rule-based suffix stripping\n"
        "- Lemmatization (WordNet) -- morphologically correct base form\n"
    )

    chunks = SentenceWindowChunker(window_size=3).chunk(text, {"filename": "notes.txt"})

    lower_chunk = next(chunk for chunk in chunks if "Lowercasing" in chunk.text)
    stemming_chunk = next(chunk for chunk in chunks if "Stemming" in chunk.text)

    assert lower_chunk.text.startswith("Text Preprocessing")
    assert stemming_chunk.text.startswith("Text Preprocessing")
    assert lower_chunk.metadata["section_heading"] == "Text Preprocessing"
    assert "Lowercasing" in lower_chunk.metadata["window_text"]
