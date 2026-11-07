"""Tests de non-régression du parsing EWS (page de secours)."""
from custom_components.dell_c1760nw.api.ews import html_to_text, parse_ews_html
from custom_components.dell_c1760nw.models import DellPrinterData


def test_textual_toner_status_does_not_create_percentage():
    data = DellPrinterData()
    assert parse_ews_html("<div>Cartouche cyan Niveau : Remplacer bientôt</div>", data)
    assert data.toner_cyan is None
    assert data.toner_status_cyan == "Remplacer bientôt"


def test_real_ews_percentage_is_kept_as_measurement():
    data = DellPrinterData()
    parse_ews_html("<div>Cartouche cyan Niveau : 42%</div>", data)
    assert data.toner_cyan == 42


def test_values_split_across_html_cells_are_parsed():
    html = (
        "<table><tr><td>Cartouche cyan</td><td>Niveau : 42%</td></tr>"
        "<tr><td>Cartouche noir</td><td>Niveau : Remplacer bientôt</td></tr></table>"
        "<script>var bourrage = 1;</script>"
    )
    data = DellPrinterData()
    assert parse_ews_html(html, data)
    assert data.toner_cyan == 42
    assert data.toner_status_black == "Remplacer bientôt"
    # Le texte d'un <script> ou d'un menu ne doit plus déclencher de faux positifs.
    assert data.paper_jam is False
    assert "bourrage" not in html_to_text(html)


def test_unknown_page_reports_nothing_found():
    assert parse_ews_html("<html><body>Hello</body></html>", DellPrinterData()) is False
