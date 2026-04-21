from pathlib import Path

from openpyxl import Workbook

from app.etl.import_flaechenatlas import parse_flaechenatlas_rows


def test_parse_flaechenatlas_rows_extracts_expected_metrics(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["header"])
    sheet.append(["header"])
    sheet.append(["header"])
    sheet.append(["01001000", "Flensburg", "6,49", "54,25", "20,34", "14,29", "318,99"])

    target = tmp_path / "flaechenatlas.xlsx"
    workbook.save(target)

    rows = parse_flaechenatlas_rows(target)

    assert len(rows) == 1
    assert rows[0]["region_ars"] == "01001000"
    assert rows[0]["forest_share_pct"] == 6.49
    assert rows[0]["settlement_transport_sqm_per_capita"] == 318.99
