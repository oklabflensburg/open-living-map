# Wohnort-Kompass

Wohnort-Kompass ist ein Monorepo fuer einen datenbasierten Wohnortvergleich fuer Gemeinden in Deutschland. Das Projekt kombiniert:

- ein `FastAPI`-Backend mit `SQLModel`, `Alembic` und `PostGIS`
- eine `Nuxt 3`-Web-App mit Finder, Ranking, Vergleich und Regionsdetailseiten
- mehrere ETL-Jobs fuer BKG, Destatis, DWD, UBA, OSM, OSM-Postleitzahlen, OePNV und Unfallatlas

## Inhalt

- [Wohnort-Kompass](#wohnort-kompass)
  - [Inhalt](#inhalt)
  - [Ueberblick](#ueberblick)
  - [Architektur](#architektur)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Datenbank](#datenbank)
  - [Repo-Struktur](#repo-struktur)
  - [Voraussetzungen](#voraussetzungen)
  - [Lokales Setup](#lokales-setup)
    - [1. Datenbank starten](#1-datenbank-starten)
    - [2. Backend einrichten](#2-backend-einrichten)
    - [3. Frontend einrichten](#3-frontend-einrichten)
  - [Konfiguration](#konfiguration)
    - [Backend](#backend-1)
    - [Frontend](#frontend-1)
  - [ETL und Datenquellen](#etl-und-datenquellen)
    - [BKG](#bkg)
    - [Destatis / Regionalstatistik](#destatis--regionalstatistik)
    - [DWD](#dwd)
    - [UBA](#uba)
    - [Unfallatlas](#unfallatlas)
    - [OSM](#osm)
    - [OSM-Postleitzahlen](#osm-postleitzahlen)
    - [OePNV](#oepnv)
    - [Score-Build](#score-build)
  - [API](#api)
  - [Frontend](#frontend-2)
  - [Entwicklung und Qualitaet](#entwicklung-und-qualitaet)
    - [Backend](#backend-2)
    - [Frontend](#frontend-3)
    - [CI](#ci)
  - [Betriebshinweise](#betriebshinweise)
    - [Schema-Disziplin](#schema-disziplin)
    - [ETL-Auditing](#etl-auditing)
    - [Logs](#logs)
    - [Datenverzeichnisse](#datenverzeichnisse)
    - [Tile- und Kartenhinweis](#tile--und-kartenhinweis)
  - [Lizenz und Attribution](#lizenz-und-attribution)
  - [Praktische Empfehlung](#praktische-empfehlung)

## Ueberblick

Die Anwendung berechnet Scores fuer sieben Kategorien:

- `climate`
- `air`
- `safety`
- `demographics`
- `amenities`
- `landuse`
- `oepnv`

Auf Basis dieser Teilscores entstehen:

- ein neutraler Gesamtscore pro Region
- ein personalisierter Profilscore auf Basis der Finder-Gewichte
- Top-100-Rankings je Kategorie und Bundesland
- Vergleichsansichten fuer bis zu drei Regionen

Der aktuelle Stand des Projekts umfasst unter anderem:

- Coverage-Felder je Kategorie statt Missing-Data-als-`0`
- trust-/qualitaetsnahe UI-Hinweise fuer Coverage, Frische und Proxy-Flags
- serverseitigen Regions-Autocomplete fuer Gemeinde, PLZ oder AGS
- URL-state fuer Finder und Ranking
- ETL-Run-Auditing
- strukturierte JSON-Logs
- Schema-Drift-Checks beim App-Start

## Architektur

### Backend

Das Backend liegt unter `backend/` und stellt die API unter `/api/v1` bereit.

Wichtige Schichten:

- `app/api/routes`
  FastAPI-Endpunkte
- `app/services`
  fachliche Logik fuer Scoring, Regionen und Erklaertexte
- `app/repositories`
  Datenbankzugriffe
- `app/models`
  SQLModel-Tabellen
- `app/schemas`
  API-Response- und Request-Modelle
- `app/etl`
  Import- und Materialisierungsjobs

Besonderheiten:

- Das Backend fuehrt keine Runtime-DDL mehr aus.
- Beim Start wird das DB-Schema geprueft.
- Wenn Migrationen fehlen, startet die App bewusst nicht.

### Frontend

Das Frontend liegt unter `frontend/` und basiert auf `Nuxt 3`, `Pinia`, `Tailwind CSS` und `Leaflet`.

Zentrale Seiten:

- `/finder`
  Gewichtungen festlegen
- `/results`
  personalisierte Empfehlungen
- `/compare`
  neutraler Vergleich von bis zu drei Regionen
- `/region/[slug]`
  Detailansicht mit Scores, Quellen, Datenbasis, Karten und Stationen
- `/top-100/[stateCode]/[category]`
  Top-100-Listen je Kategorie
- `/methodik`
  Datenquellen und fachliche Einordnung

### Datenbank

Die lokale Entwicklungsumgebung nutzt `postgis/postgis:16-3.4`.

Wichtige Tabellen und Schemas:

- `region`
- `region_score_snapshot`
- `region_indicator_value`
- `indicator_definition`
- `geo.municipality_boundary`
- `postal.region_postal_code`
- `postal.postal_area_stage`
- `climate.region_climate_station`
- `etl_run`
- `etl_run_source`

## Repo-Struktur

```text
open-living-map/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── etl/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── components/
│   ├── composables/
│   ├── pages/
│   ├── server/routes/
│   ├── stores/
│   ├── types/
│   ├── package.json
│   └── .env.example
├── infra/
│   └── docker-compose.yml
└── README.md
```

## Voraussetzungen

- Python `3.12`
- Node.js `20+`
- `pnpm`
- Docker + Docker Compose
- `ogr2ogr` aus GDAL fuer den BKG-Import
- optional `osm2pgsql` fuer den OSM-Rohimport

## Lokales Setup

### 1. Datenbank starten

```bash
cd infra
docker compose up -d
```

Standardmaessig laeuft PostGIS danach auf `localhost:5433`.

### 2. Backend einrichten

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Backend:

- App: `http://localhost:8000`
- API: `http://localhost:8000/api/v1`

### 3. Frontend einrichten

```bash
cd frontend
pnpm install
cp .env.example .env
pnpm dev
```

Frontend:

- App: `http://localhost:3000`

## Konfiguration

### Backend

Alle Backend-Settings werden aus [backend/.env.example](backend/.env.example) abgeleiteten Werten in `backend/.env` geladen.

Wesentliche Schalter:

- `DATABASE_URL`
  Datenbankverbindung
- `API_PREFIX`
  Standard: `/api/v1`
- `CORS_ALLOW_ORIGINS`
  lokale Nuxt-Origin(s)
- `RAW_DATA_DIR`
  Rohdatenverzeichnis
- `STAGING_DATA_DIR`
  Staging-/Zwischendaten
- `GENESIS_USERNAME`, `GENESIS_PASSWORD`
  Zugang fuer Destatis/Regionalstatistik
- `DWD_BASE_URL`
  DWD Daily KL
- `DWD_MAX_STATIONS`
  optionales Stationslimit fuer Testlaeufe
- `DWD_RECENT_CACHE_MAX_AGE_HOURS`
  Refresh-Fenster fuer lokale DWD-`recent`-Dateien
- `UBA_API_BASE`
  Umweltbundesamt-API
- `BKG_MUNICIPALITY_TABLE`
  lokale BKG-Gemeindetabelle
- `BKG_DISTRICT_TABLE`
  lokale BKG-Kreistabelle
- `BKG_GEOMETRY_COLUMN`
  Geometriespalte der BKG-Tabelle
- `BKG_GEOMETRY_FLAVOUR`
  bevorzugter BKG-`gf`-Wert
- `OEPNV_GTFS_URLS`
  komma-separierte GTFS-Quellen
- `OEPNV_HTTP_USERNAME`, `OEPNV_HTTP_PASSWORD`
  optional fuer geschuetzte GTFS-Endpunkte

### Frontend

Die wichtigsten Variablen stehen in [frontend/.env.example](frontend/.env.example).

Wesentliche Schalter:

- `NUXT_PUBLIC_API_BASE`
  Basis-URL der API
- `NUXT_PUBLIC_SITE_URL`
  oeffentliche Basis-URL
- `NUXT_PUBLIC_REPO_URL`
  Repository-Link fuer Footer und SEO
- `NUXT_PUBLIC_LEGAL_*`
  Inhalte fuer Impressum und Datenschutz

## ETL und Datenquellen

Die ETL-Jobs liegen unter `backend/app/etl`.

Typische Reihenfolge:

```bash
cd backend
./venv/bin/python -m app.etl.import_bkg
./venv/bin/python -m app.etl.import_destatis
./venv/bin/python -m app.etl.import_dwd
./venv/bin/python -m app.etl.import_uba
./venv/bin/python -m app.etl.import_unfallatlas
./venv/bin/python -m app.etl.import_osm
./venv/bin/python -m app.etl.import_postal_codes
./venv/bin/python -m app.etl.import_oepnv
./venv/bin/python -m app.etl.build_scores
```

### BKG

`import_bkg` erwartet eine lokal importierte Gemeindetabelle, standardmaessig `public.vg25_gem`.

Der Job:

- materialisiert Gemeinden nach `region`
- schreibt Gemeindegrenzen nach `geo.municipality_boundary`
- pflegt `district_name`, `slug`, `wikidata_*`, `wikipedia_url`

Beispiel fuer einen lokalen Import mit GDAL:

```bash
ogr2ogr -f "PostgreSQL" \
  PG:"dbname=wohnortkompass user=wohnortkompass port=5433 host=localhost" \
  /pfad/zu/DE_VG25.gpkg vg25_gem \
  -lco GEOMETRY_NAME=geom -lco SPATIAL_INDEX=GIST -lco PRECISION=NO \
  -t_srs EPSG:4326 -nlt MULTIPOLYGON -overwrite -update
```

### Destatis / Regionalstatistik

`import_destatis` verarbeitet gemeindescharfe Demografie und verwandte Indikatoren aus der Regionalstatistik / GENESIS.

Aktuell genutzt werden unter anderem:

- Einwohner gesamt
- Frauenanteil
- Anteil unter 18 Jahren
- Anteil ab 65 Jahren

### DWD

`import_dwd` verarbeitet aktuelle DWD-Tageswerte fuer das Daily-KL-Produkt.

Abgeleitete Indikatoren:

- Hitzetage
- Sommertage
- Niederschlag

Wichtig:

- es werden rollierende Kennzahlen auf Basis aktueller DWD-`recent`-Dateien gebildet
- `recent`-ZIPs werden lokal zwischengespeichert
- ein Re-Download erfolgt, wenn die Datei fehlt oder aelter als `DWD_RECENT_CACHE_MAX_AGE_HOURS` ist
- fuer Regionen wird die naechstgelegene DWD-Station dokumentiert und in der Detailseite angezeigt

### UBA

`import_uba` verarbeitet Luftqualitaetsdaten des Umweltbundesamts.

Aktuell genutzt werden:

- `NO2`
- `PM10`
- `PM2.5`

Die Detailseite zeigt die zugeordnete Luftmessstation inklusive Stationsname und UBA-Seitenlink.

### Unfallatlas

`import_unfallatlas` verarbeitet Unfallorte und daraus abgeleitete Sicherheitsindikatoren.

### OSM

`import_osm` verarbeitet alltagsrelevante POIs und weitere OSM-basierte Informationen.

Genutzt werden unter anderem:

- Alltagsnaehe / Amenity-Dichten
- POI-Overlays fuer die Karten
- materialisierte `amenity_poi_stage`-Tabellen fuer schnellere Regionsabfragen

### OSM-Postleitzahlen

`import_postal_codes` materialisiert OSM-Postleitzahlflaechen und mappt sie auf Gemeinden.

Ziel:

- Suche nach PLZ, Gemeindename oder AGS/ARS
- exakte 5-stellige PLZ werden auf eine primaere Gemeinde gemappt
- unscharfe PLZ- oder Namenssuchen koennen mehrere Treffer liefern

Technisch:

- `postal.postal_area_stage` als vorgelagerte Stage fuer PLZ-Flaechen
- `postal.region_postal_code` als Zuordnungstabelle
- GiST-Indizes fuer den raeumlichen Join

### OePNV

`import_oepnv` verarbeitet GTFS-Daten.

Aktuell genutzte OePNV-Indikatoren:

- Haltestellendichte
- Abfahrten je 10.000 Einwohner
- Angebotsmasse
- Abfahrtsregelmaessigkeit

Die OePNV-Kategorie ist fachlich intern gewichtet und nicht mehr nur ein einfacher Mittelwert.

### Score-Build

`build_scores` berechnet aus den materialisierten Indikatoren:

- Kategoriescores
- neutralen Gesamtscore
- Coverage-Felder je Kategorie

Fehlende Kategorien werden dabei nicht mehr pauschal als `0` gewertet.

## API

Wichtige Endpunkte:

- `GET /api/v1/health`
- `GET /api/v1/regions`
- `GET /api/v1/regions/search/autocomplete`
- `GET /api/v1/regions/state-boundaries`
- `GET /api/v1/regions/{ars}`
- `GET /api/v1/regions/{ars}/amenities/{category}`
- `GET /api/v1/regions/{ars}/accidents/{category}`
- `POST /api/v1/recommendations`
- `GET /api/v1/compare?ars=...`
- `GET /api/v1/rankings/top/{category}`
- `GET /api/v1/rankings/top/{state_code}/{category}`
- `GET /api/v1/metadata/indicators`

Beispiele:

```bash
curl 'http://localhost:8000/api/v1/regions/search/autocomplete?q=24937&limit=8'
curl 'http://localhost:8000/api/v1/regions/01001000'
curl 'http://localhost:8000/api/v1/compare?ars=01001000,01059113,08116053'
```

## Frontend

Wichtige Frontend-Eigenschaften:

- Finder und Ranking-Zustand sind ueber Query-Parameter teilbar
- Compare nutzt Pinia und URL-State
- Regionsdetailseiten zeigen:
  - Scores
  - Datenbasis und Aktualitaet
  - Qualitaets- und Proxy-Hinweise
  - Luft- und Klimastationen
  - thematische Kartenlayer
- Suche im Header arbeitet serverseitig ueber Autocomplete

## Entwicklung und Qualitaet

### Backend

Installieren:

```bash
cd backend
pip install -e .
```

Nutzt:

- `ruff`
- `pytest`
- `alembic`

Wichtige Checks:

```bash
cd backend
ruff check .
python -m py_compile $(find . -name '*.py' -type f)
pytest
alembic upgrade head
```

Vorhandene Tests:

- `backend/tests/etl/test_import_bkg.py`
- `backend/tests/etl/test_import_destatis.py`
- `backend/tests/etl/test_import_dwd.py`
- `backend/tests/etl/test_import_flaechenatlas.py`

### Frontend

Wichtige Checks:

```bash
cd frontend
pnpm install
pnpm run typecheck
pnpm run build
```

### CI

Die GitHub-Actions-Pipeline unter [.github/workflows/ci.yml](.github/workflows/ci.yml) fuehrt aus:

- Backend-Lint
- Python-Syntaxcheck
- `pytest`
- Alembic-Check
- Import-Smoke-Checks
- Frontend-Typecheck
- Frontend-Build

## Betriebshinweise

### Schema-Disziplin

Die Anwendung startet nur, wenn das DB-Schema zum Code passt.

Wenn die App mit `SchemaDriftError` abbricht:

```bash
cd backend
./venv/bin/alembic upgrade head
```

Wichtige Regel:

- Schema-Aenderungen ausschliesslich per Alembic
- keine Runtime-DDL
- bereits ausgefuehrte Migrationen nicht nachtraeglich erweitern

### ETL-Auditing

Wichtige ETLs schreiben Run-Metadaten nach:

- `etl_run`
- `etl_run_source`

Damit sind Start, Ende, Status, Fehltext und grobe `rows_written` nachvollziehbar.

### Logs

Backend und ETLs loggen strukturiert im JSON-Format.

API-Requests enthalten unter anderem:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

### Datenverzeichnisse

Roh- und Staging-Daten werden ueber `RAW_DATA_DIR` und `STAGING_DATA_DIR` konfiguriert.

Standard in [backend/.env.example](backend/.env.example):

- `RAW_DATA_DIR=../../data/raw`
- `STAGING_DATA_DIR=../../data/staging`

Wenn du diese Defaults uebernimmst, liegen die Daten ausserhalb von `backend/` und `frontend/`.

### Tile- und Kartenhinweis

Die Anwendung nutzt Leaflet und externe Kartentiles. Eine ausgearbeitete Tile-Provider-Strategie ist noch kein abgeschlossener Teil des Repos und sollte vor produktivem Betrieb sauber dokumentiert und abgesichert werden.

## Lizenz und Attribution

Dieses Repo vereint Daten aus verschiedenen Quellen mit jeweils eigenen Lizenz- und Nutzungsbedingungen. Vor oeffentlichem Betrieb solltest du die Bedingungen der verwendeten Quellen pruefen und korrekt ausweisen.

Wesentliche Quellen:

- OpenStreetMap
- BKG VG25
- Destatis / Regionalstatistik / GENESIS
- Deutscher Wetterdienst
- Umweltbundesamt
- Unfallatlas / Destatis
- GTFS-Feeds aus OpenData OePNV

Fuer OSM gilt insbesondere:

- Daten: `ODbL`
- Karten-/Tile-Nutzung: eigene Nutzungsbedingungen des gewaehlten Tile-Providers beachten

## Praktische Empfehlung

Wenn du lokal von null startest, ist das die stabilste Reihenfolge:

1. PostGIS starten
2. Backend-Dependencies installieren
3. `alembic upgrade head`
4. BKG-Gemeindetabelle lokal importieren
5. ETLs in der empfohlenen Reihenfolge ausfuehren
6. `build_scores` laufen lassen
7. Backend starten
8. Frontend starten

Damit hast du einen konsistenten Stand fuer Finder, Ranking, Compare, Top-100 und Regionsdetailseiten.
