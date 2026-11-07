"""Tests de non-régression du parsing EWS."""
from custom_components.dell_c1760nw.api.ews import parse_ews_html
from custom_components.dell_c1760nw.models import DellPrinterData


def test_textual_toner_status_does_not_create_percentage():
    data = DellPrinterData()
    parse_ews_html("<div>Cartouche cyan Niveau : Remplacer bientôt</div>", data)
    assert data.toner_cyan is None
    assert data.toner_status_cyan is not None


def test_real_ews_percentage_is_kept_as_measurement():
    data = DellPrinterData()
    parse_ews_html("<div>Cartouche cyan Niveau : 42%</div>", data)
    assert data.toner_cyan == 42
