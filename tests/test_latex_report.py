"""LaTeX export must preserve content without interpreting data as TeX syntax."""

from scripts.latex_report import LatexReport, latex_escape, report_text


def test_special_characters_and_report_emphasis_are_preserved():
    assert latex_escape("a_b & 50%") == r"a\_b \& 50\%"
    assert report_text("<b>SOC</b><br/>min &lt;= actual") == r"\textbf{SOC}\newline{}min <= actual"
    assert report_text("a_b<br/>--output result", plain=True) == "a_b\n--output result"


def test_source_contains_editable_table_and_document_boundaries(tmp_path):
    output=tmp_path/"main.tex"
    report=LatexReport(output)
    report.paragraph("Team guide", "Title")
    report.table([["Key","Value"],["battery_soc","20%"]],[1,1])
    report.write()
    text=output.read_text()
    assert r"\begin{document}" in text and r"\end{document}" in text
    assert r"\begin{longtable}" in text and r"battery\_\allowbreak{}soc" in text
    assert r"20\%" in text
