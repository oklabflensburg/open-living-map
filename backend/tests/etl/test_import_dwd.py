from pathlib import Path

from app.etl.import_dwd import _parse_station_file


def test_parse_station_file_parses_fixed_width_rows(tmp_path: Path) -> None:
    station_file = tmp_path / "stations.txt"
    station_file.write_text(
        "\n".join(
            [
                "Kopfzeile 1",
                "Kopfzeile 2",
                "00091 20200101 20251231    12   54.78    9.43 Flensburg Schleswig-Holstein",
                "00123 20200101 20251231    15   53.55   10.00 Hamburg Hamburg",
            ]
        ),
        encoding="latin1",
    )

    parsed = _parse_station_file(station_file)

    assert list(parsed["station_id"]) == ["00091", "00123"]
    assert round(float(parsed.iloc[0]["lat"]), 2) == 54.78
    assert round(float(parsed.iloc[0]["lon"]), 2) == 9.43
