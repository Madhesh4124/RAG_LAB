import pytest
from app.services.pdf_table_extractor import _df_from_table, _table_to_markdown
import pandas as pd


def test_df_from_table_rectangular():
    table = [["A", "B"], ["1", "2"], ["3"]]
    df = _df_from_table(table)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[1] == 2


def test_table_to_markdown_header_promotion():
    df = pd.DataFrame([["h1", "h2"], ["a", "b"]])
    md = _table_to_markdown(df)
    assert "| h1 | h2 |" in md
    assert "| a | b |" in md


def test_table_to_markdown_multilevel_header():
    # Like benchmark tables with subheaders (CN, EN) under metrics
    raw = [
        ["Model", "Completeness", None, "BLEU", None],
        [None, "CN", "EN", "CN", "EN"],
        ["MiniCPM", "54.59", "57.88", "15.19", "6.38"],
    ]
    df = _df_from_table(raw)
    md = _table_to_markdown(df)
    assert "| Model | Completeness CN | Completeness EN | BLEU CN | BLEU EN |" in md
    assert "| MiniCPM | 54.59 | 57.88 | 15.19 | 6.38 |" in md

