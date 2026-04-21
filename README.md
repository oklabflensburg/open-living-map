# Wohnortkompass

Wohnortkompass ist ein lokales Monorepo fuer eine Deutschlandkarte mit kommunalen Wohnortindikatoren. Das Projekt kombiniert einen FastAPI-Backend-Stack mit einer Nuxt-Frontend-App und mehreren ETL-Jobs fuer Geometrien, Demografie, Klima, Luftqualitaet, OSM-POIs, OSM-Postleitzahlen, OePNV und Unfallatlas-Daten.

## Inhalt

- [Wohnortkompass](#wohnortkompass)
  - [Inhalt](#inhalt)
  - [Ueberblick](#ueberblick)
  - [Projektstruktur](#projektstruktur)
  - [Voraussetzungen](#voraussetzungen)
  - [Lokales Setup](#lokales-setup)
    - [1. Datenbank starten](#1-datenbank-starten)
    - [2. Backend einrichten](#2-backend-einrichten)
    - [3. Frontend einrichten](#3-frontend-einrichten)
  - [Umgebungsvariablen](#umgebungsvariablen)
    - [Backend](#backend)
    - [Frontend](#frontend)
  - [Datenquellen und ETL](#datenquellen-und-etl)
    - [BKG VG25](#bkg-vg25)
    - [Destatis / Regionalstatistik](#destatis--regionalstatistik)
    - [DWD](#dwd)
    - [UBA](#uba)
    - [Unfallatlas](#unfallatlas)
    - [OSM](#osm)
    - [OSM-Postleitzahlen](#osm-postleitzahlen)
  - [Lizenz und Attribution](#lizenz-und-attribution)
    - [OpenStreetMap](#openstreetmap)
    - [BKG VG25](#bkg-vg25-1)
    - [Destatis / Regionalstatistik / GENESIS](#destatis--regionalstatistik--genesis)
    - [DWD](#dwd-1)
    - [Umweltbundesamt](#umweltbundesamt)
    - [Unfallatlas](#unfallatlas-1)
    - [GTFS-Datenquellen aus OpenData OePNV](#gtfs-datenquellen-aus-opendata-oepnv)
  - [Praktische Empfehlung fuer das Projekt](#praktische-empfehlung-fuer-das-projekt)
    - [OePNV](#oepnv)
  - [API](#api)
  - [Frontend](#frontend-1)
  - [Datenbank und Persistenz](#datenbank-und-persistenz)
  - [Bekannte Besonderheiten](#bekannte-besonderheiten)
  - [Lizenz und Attribution](#lizenz-und-attribution-1)

## Ueberblick

Das System besteht aus drei Hauptteilen:

1. `backend`
   FastAPI, SQLModel, Alembic und die ETL-Jobs.
2. `frontend`
   Nuxt 3 mit Kartenansichten, Finder, Vergleich und Regions-Detailseiten.
3. `infra`
   Lokale PostGIS-Datenbank per Docker Compose.

Die App arbeitet gemeindescharf, soweit die jeweiligen Quellen das hergeben. Geometrien kommen lokal aus BKG VG25, Demografie aus der Regionalstatistik, OSM-Alltagsnaehe aus `osm2pgsql`, OePNV aus GTFS und Unfallorte aus dem Unfallatlas.

## Projektstruktur

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
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── components/
│   ├── composables/
│   ├── pages/
│   ├── stores/
│   ├── types/
│   ├── nuxt.config.ts
│   └── .env.example
├── infra/
│   └── docker-compose.yml
└── README.md
```

Zusatzdaten werden ausserhalb des App-Codes unter `../data/` gespeichert:

- `data/raw`
  heruntergeladene Rohdaten wie BKG, DWD, GTFS, Unfallatlas, OSM-PBF
- `data/staging`
  temporaere ETL-Artefakte

## Voraussetzungen

- Python `3.12`
- Node.js `20+`
- `pnpm`
- Docker + Docker Compose
- `ogr2ogr` aus GDAL fuer den BKG-VG25-Import
- optional `osm2pgsql` fuer OSM-Rohimporte

## Lokales Setup

### 1. Datenbank starten

```bash
cd infra
docker compose up -d
```

Die Datenbank ist danach unter `localhost:5433` verfuegbar.

### 2. Backend einrichten

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend-Standardadresse:

- `http://localhost:8000`
- API-Basis: `http://localhost:8000/api/v1`

### 3. Frontend einrichten

```bash
cd frontend
pnpm install
cp .env.example .env
pnpm dev
```

Frontend-Standardadresse:

- `http://localhost:3000`

Die Nuxt-App spricht standardmaessig mit:

- `NUXT_PUBLIC_API_BASE=http://localhost:8000/api/v1`

## Umgebungsvariablen

### Backend

Wichtige Variablen aus `backend/.env.example`:

- `DATABASE_URL`
  SQLAlchemy/psycopg-Verbindung zur PostGIS-Datenbank
- `GENESIS_USERNAME`, `GENESIS_PASSWORD`
  Zugang zur Regionalstatistik/GENESIS
- `GENESIS_API_URL`
  standardmaessig Regionalstatistik REST `data/table`
- `BKG_MUNICIPALITY_TABLE`
  lokale BKG-Gemeindetabelle, standardmaessig `public.vg25_gem`
- `BKG_GEOMETRY_COLUMN`
  Geometriespalte der BKG-Tabelle, standardmaessig `geom`
- `BKG_GEOMETRY_FLAVOUR`
  bevorzugter `gf`-Wert fuer BKG-Geometrien
- `OEPNV_GTFS_URLS`
  komma-separierte GTFS-ZIP-Quellen
- `DWD_MAX_STATIONS`
  optionales Limit fuer Testlaeufe

### Frontend

Aus `frontend/.env.example`:

- `NUXT_PUBLIC_API_BASE`
  Basis-URL der API

## Datenquellen und ETL

Die ETL-Jobs sitzen unter `backend/app/etl`.

Typische Reihenfolge:

```bash
cd backend
python -m app.etl.import_bkg
python -m app.etl.import_destatis
python -m app.etl.import_dwd
python -m app.etl.import_uba
python -m app.etl.import_unfallatlas
python -m app.etl.import_osm
python -m app.etl.import_postal_codes
python -m app.etl.import_oepnv
python -m app.etl.build_scores
```

### BKG VG25

`import_bkg` erwartet eine lokal importierte Gemeindetabelle in PostGIS. Standard:

- Tabelle: `public.vg25_gem`
- Geometriespalte: `geom`

Minimaler Import:

```bash
ogr2ogr -f "PostgreSQL" \
  PG:"dbname=wohnortkompass user=wohnortkompass port=5433 host=localhost" \
  /pfad/zu/DE_VG25.gpkg vg25_gem \
  -lco GEOMETRY_NAME=geom -lco SPATIAL_INDEX=GIST -lco PRECISION=NO \
  -t_srs EPSG:4326 -nlt MULTIPOLYGON -overwrite -update
```

Empfohlene Indizes:

```sql
CREATE INDEX IF NOT EXISTS idx_vg25_gem_ags ON vg25_gem (ags);
CREATE INDEX IF NOT EXISTS idx_vg25_gem_gf ON vg25_gem (gf);
CREATE INDEX IF NOT EXISTS idx_gem_sn_k ON vg25_gem (sn_k);
CREATE INDEX IF NOT EXISTS idx_gem_sn_r ON vg25_gem (sn_r);
CREATE INDEX IF NOT EXISTS idx_gem_sn_l ON vg25_gem (sn_l);
```

Was `import_bkg` macht:

- liest Gemeinden aus der lokalen BKG-Tabelle
- schreibt `region`
- schreibt Grenzen nach `geo.municipality_boundary`
- reichert Regionen mit `wikidata_id`, `wikidata_url`, `wikipedia_url` an
- nutzt XRepository als Referenz fuer den AGS-Schluesselraum

### Destatis / Regionalstatistik

`import_destatis` zieht gemeindescharfe Demografie aus der Regionalstatistik.

Aktuell werden insbesondere diese Kategorien gepflegt:

- Gesamtbevoelkerung
- Frauenanteil
- Anteil unter 18 Jahren
- Anteil ab 65 Jahren

Besonderheiten:

- Der Import kann grosse Tabellen ueber den GENESIS-Jobmechanismus im Hintergrund laden.
- Bei fehlender BKG-Einwohnerspalte wird `region.population` aus `population_total_destatis` nachgefuehrt.
- Kreisfreie Staedte werden ueber die speziellen Regionalstatistik-Codes ebenfalls gemappt.

### DWD

`import_dwd` verarbeitet echte DWD-Tageswerte.

Beispiele:

- Hitzetage
- Sommertage
- Niederschlags-Proxies

### UBA

`import_uba` zieht Luftqualitaetsdaten, u. a.:

- `NO2`
- `PM10`
- `PM2.5`

### Unfallatlas

`import_unfallatlas` laedt das neueste Unfallatlas-CSV-ZIP und verarbeitet es jetzt gemeindescharf.

Aktuell:

- aggregierter Sicherheitsindikator `road_accidents_total`
- Unfallpunkte als GeoJSON-Grundlage in `traffic.accident_point`
- Kategorien technisch auf Englisch:
  - `killed`
  - `seriously_injured`
  - `slightly_injured`
- Frontend-Labels bleiben deutsch:
  - `Getoetete`
  - `Schwerverletzte`
  - `Leichtverletzte`

### OSM

`import_osm` nutzt `osm2pgsql`-Tabellen und Gemeindegrenzen, um Alltagsnaehe zu aggregieren.

### OSM-Postleitzahlen

`import_postal_codes` nutzt lokal importierte OSM-Postleitzahlgebiete aus `osm.planet_osm_polygon`.

Was der Import macht:

- liest OSM-Polygone mit `boundary=postal_code`
- extrahiert die 5-stellige PLZ aus `postal_code` oder `addr:postcode`
- mappt die PLZ-Flaechen per raeumlichem Join auf `geo.municipality_boundary`
- schreibt die Gemeinde-PLZ-Zuordnung nach `postal.region_postal_code`

Wofuer das genutzt wird:

- Header-Suche
- Compare-Suche
- API-Suche `/api/v1/regions/search/autocomplete`

Die Suche akzeptiert damit:

- Gemeindename
- AGS
- PLZ

Hinweis:

- eine PLZ kann mehreren Gemeinden zugeordnet sein
- in diesem Fall liefert die Suche mehrere fachlich korrekte Gemeindetreffer

## Lizenz und Attribution

Bitte die Lizenz- und Attributionspflichten der eingebundenen Datenquellen beachten. Die folgende Uebersicht beschreibt den aktuell verwendeten Stand der im Projekt genutzten Quellen. Im Zweifel gilt immer die Lizenzangabe direkt am konkreten Datensatz oder Dienst.

### OpenStreetMap

- Lizenz: `Open Data Commons Open Database License (ODbL) 1.0`
- Mindestattribution: `© OpenStreetMap-Mitwirkende`
- Zusaetzlich muss kenntlich gemacht werden, dass die Daten unter ODbL stehen.
- Quelle:
  - https://www.openstreetmap.org/copyright

### BKG VG25

- Datensatz: `Verwaltungsgebiete 1:25 000 (VG25)`
- Lizenz: `CC BY 4.0`
- Quellenvermerk laut BKG:
  - `© BKG (Jahr des letzten Datenbezugs) CC BY 4.0, Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg25.pdf`
- Bei veraenderten Daten ist ein Veraenderungshinweis anzubringen.
- Quellen:
  - https://gdz.bkg.bund.de/index.php/default/digitale-geodaten/verwaltungsgebiete/verwaltungsgebiete-1-25-000-stand-31-12-vg25.html
  - https://www.bkg.bund.de

### Destatis / Regionalstatistik / GENESIS

- Lizenz: `Datenlizenz Deutschland – Namensnennung – Version 2.0`
- Kurzform: `dl-de/by-2-0`
- Empfohlener Quellenvermerk:
  - `Datenquelle: Statistisches Bundesamt (Destatis), Genesis-Online, <Abrufdatum>; Datenlizenz by-2-0`
- Bei eigener Berechnung oder Darstellung sollte dies im Quellenvermerk kenntlich gemacht werden.
- Quellen:
  - https://www.destatis.de/DE/Service/OpenData/genesis-api-webservice-oberflaeche.html
  - https://www.destatis.de/DE/Service/Impressum/copyright-genesis-online.html

### DWD

- Fuer die im Projekt genutzten DWD-Open-Data- bzw. CDC-Daten ist `CC BY 4.0` dokumentiert.
- Empfohlene Attribution: `Quelle: Deutscher Wetterdienst (DWD)`
- Die konkrete Datensatzdokumentation des jeweils genutzten Open-Data-Produkts ist zusaetzlich zu beachten.
- Quellen:
  - https://opendata.dwd.de/climate_environment/REA/Nutzungsbedingungen_German.pdf
  - https://www.dwd.de/EN/ourservices/cdc/cdc.html

### Umweltbundesamt

- UBA unterscheidet zwischen Website-Inhalten und bereitgestellten Daten.
- Website-Texte, Grafiken und Medien stehen, soweit nicht anders gekennzeichnet, unter `CC BY-NC-ND 4.0`.
- Fuer bereitgestellte Daten und Metadaten weist das UBA ausdruecklich auf deren zulaessige Nutzung hin; massgeblich bleiben die Bedingungen des jeweiligen Datenangebots.
- Empfehlung fuer das Projekt:
  - Datenseitige Attribution immer direkt am konkret verwendeten UBA-Dienst oder Datensatz pruefen.
  - Website-Lizenz nicht pauschal auf die Fachdaten uebertragen.
- Quelle:
  - https://luftdaten.umweltbundesamt.de/datenschutz-haftung-und-urheberrecht

### Unfallatlas

- Die Unfallatlas-Daten werden als Open Data ueber das Statistikportal bereitgestellt.
- Die Open-Data-Seiten des Statistikportals verweisen fuer statistische Daten allgemein auf die `Datenlizenz Deutschland 2.0`.
- Bei kartografischen Anwendungen koennen fuer zusaetzliche Geobasisdaten gesonderte Lizenzhinweise gelten.
- Da der Unfallatlas als Statistikportal-Open-Data-Angebot beschrieben ist, ist `dl-de/by-2-0` hier die naheliegende Lizenzgrundlage.
- Quellen:
  - https://www.statistikportal.de/de/karten/unfallatlas
  - https://www.statistikportal.de/de/open-data

Hinweis: Die konkrete Open-Data-Downloadseite des Unfallatlas sollte bei produktiver Veroeffentlichung nochmals auf einen expliziten Lizenztext geprueft werden.

### GTFS-Datenquellen aus OpenData OePNV

- Das Portal `OpenData OePNV` hat keine einheitliche Datenlizenz fuer alle Datensaetze.
- Laut Portal ist fuer die Lizenzierung jeweils der konkrete Datenanbieter zustaendig.
- Fuer den im Projekt verwendeten deutschlandweiten `DELFI GTFS`-Datensatz ist aktuell `Creative Commons Namensnennung (CC-BY)` angegeben.
- Quellen:
  - https://www.opendata-oepnv.de/ht/de/standards/nutzungsbedingungen
  - https://www.opendata-oepnv.de/ht/de/organisation/delfi/startseite?cHash=af4be4c0a9de59953fb9ee2325ef818f&tx_vrrkit_view%5Baction%5D=details&tx_vrrkit_view%5Bcontroller%5D=View&tx_vrrkit_view%5Bdataset_name%5D=deutschlandweite-sollfahrplandaten-gtfs
  - https://www.opendata-oepnv.de/ht/de/standards/uebersicht-der-verwendeten-lizenzen

## Praktische Empfehlung fuer das Projekt

Bei jeder oeffentlichen Ausspielung sollten mindestens folgende Quellenhinweise sichtbar oder in einer Methodik-/Impressumsseite verlinkt sein:

- `© OpenStreetMap-Mitwirkende, ODbL 1.0`
- `© BKG <Jahr des letzten Datenbezugs>, CC BY 4.0`
- `Datenquelle: Statistisches Bundesamt (Destatis), Genesis-Online, dl-de/by-2-0`
- `Quelle: Deutscher Wetterdienst (DWD)`
- `Quelle: Umweltbundesamt (je nach Datensatz/Dienst)`
- `Quelle: Statistische Aemter des Bundes und der Laender / Unfallatlas`
- `Quelle: DELFI / OpenData OePNV, gemaess Datensatzlizenz`

Unterstuetzte Kategorien:

- `pharmacy`
- `doctors`
- `childcare`
- `school`
- `supermarket`
- `station`
- `transit_stop`
- `playground`
- `park`

Ergebnisse:

- Aggregattabelle `osm.region_amenity_agg`
- Indikator `amenities_density`
- klickbare GeoJSON-POIs je Kategorie auf der Regionsseite

### OePNV

`import_oepnv` verarbeitet GTFS und schreibt u. a.:

- `oepnv_stop_density`
- `oepnv_departures_per_10k`
- `oepnv_departure_regularity`

## API

Basis:

- `GET /api/v1/health`
- `GET /api/v1/regions`
- `GET /api/v1/regions/{ars-or-slug}`
- `POST /api/v1/recommendations`
- `GET /api/v1/compare?ars=...`
- `GET /api/v1/metadata/indicators`

Interaktive Karten-Endpunkte:

- `GET /api/v1/regions/{ars}/amenities/{category}`
- `GET /api/v1/regions/{ars}/accidents/{category}`

Beispiele:

- `/api/v1/regions/kiel/amenities/pharmacy`
- `/api/v1/regions/flensburg/accidents/slightly_injured`

Die API verwendet fuer technische Kategorien bewusst englische Keys. Die Uebersetzung in deutsch passiert im Frontend.

## Frontend

Die Nuxt-App bietet aktuell:

- Landing Page
- Finder / Empfehlungen
- Vergleich
- Methodik-Seite
- Regions-Detailseiten mit:
  - Gesamt- und Teil-Scores
  - Demografie-Block
  - OSM-Alltagsnaehe-Block
  - Verkehrsunfall-Block
  - Gemeindegrenze auf Leaflet-Karte
  - klickbare OSM-POIs auf der Karte
  - klickbare Unfallpunkte auf der Karte

Wichtige Dateien:

- `frontend/pages/index.vue`
- `frontend/pages/finder.vue`
- `frontend/pages/compare.vue`
- `frontend/pages/methodik.vue`
- `frontend/pages/region/[slug].vue`

## Datenbank und Persistenz

Zentrale Tabellen und Schemata:

- `region`
- `indicator_definition`
- `region_indicator_value`
- `region_score_snapshot`
- `geo.municipality_boundary`
- `osm.region_amenity_agg`
- `traffic.accident_point`

Docker Compose startet standardmaessig:

- PostGIS 16 / PostGIS 3.4
- DB: `wohnortkompass`
- User: `wohnortkompass`
- Port: `5433`

## Bekannte Besonderheiten

- Einige Quellen sind langsam oder erfordern Zugangsdaten, insbesondere Destatis/Regionalstatistik.
- Nicht jede BKG-Lieferung enthaelt Einwohnerfelder. In diesem Fall wird die Gesamtbevoelkerung aus Destatis nachgezogen.

## Lizenz und Attribution

Bitte die Lizenz- und Attributionspflichten der eingebundenen Datenquellen beachten, insbesondere:

- OpenStreetMap / ODbL
- BKG VG25
- Destatis / Regionalstatistik
- DWD
- Umweltbundesamt
- Unfallatlas
- GTFS-Datenquellen aus OpenData-OePNV
