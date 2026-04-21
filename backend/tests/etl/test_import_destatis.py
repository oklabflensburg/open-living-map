from app.etl.import_destatis import _parse_age_rows, _parse_population_rows


def test_parse_population_rows_handles_simple_csv_shape() -> None:
    content = "\n".join(
        [
            "01001000;Flensburg;96326;47200;49126",
            "02000000;Hamburg;1900000;930000;970000",
        ]
    )

    rows = _parse_population_rows(content)

    assert rows[0][0] == "01001000"
    assert rows[0][1]["total"] == 96326.0
    assert rows[0][1]["female"] == 49126.0


def test_parse_age_rows_handles_simple_csv_shape() -> None:
    content = "\n".join(
        [
            "1;01001000;Flensburg;Insgesamt;96326;;",
            "2;01001000;Flensburg;unter 3 Jahre;2500;;",
            "3;01001000;Flensburg;65 bis unter 75 Jahre;9000;;",
        ]
    )

    rows = _parse_age_rows(content)

    assert rows["01001000"]["insgesamt"] == 96326.0
    assert rows["01001000"]["unter 3 jahre"] == 2500.0
    assert rows["01001000"]["65 bis unter 75 jahre"] == 9000.0
