from app.etl.import_bkg import _parse_genericode_rows


def test_parse_genericode_rows_extracts_code_name_mapping() -> None:
    xml = """
    <CodeList xmlns="http://docs.oasis-open.org/codelist/ns/genericode/1.0/">
      <ColumnSet>
        <Column Id="col-code">
          <ShortName>Schluessel</ShortName>
        </Column>
        <Column Id="col-name">
          <ShortName>Bezeichnung</ShortName>
        </Column>
      </ColumnSet>
      <SimpleCodeList>
        <Row>
          <Value ColumnRef="col-code"><SimpleValue>01059</SimpleValue></Value>
          <Value ColumnRef="col-name"><SimpleValue>Schleswig-Flensburg</SimpleValue></Value>
        </Row>
      </SimpleCodeList>
    </CodeList>
    """

    rows = _parse_genericode_rows(xml)

    assert rows == {"01059": "Schleswig-Flensburg"}
