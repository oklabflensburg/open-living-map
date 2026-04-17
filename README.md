# Wohnortkompass

Wohnortkompass ist ein lokales Monorepo fuer eine Deutschlandkarte mit kommunalen Wohnortindikatoren. Das Projekt kombiniert einen FastAPI-Backend-Stack mit einer Nuxt-Frontend-App und mehreren ETL-Jobs fuer Geometrien, Demografie, Klima, Luftqualitaet, OSM-POIs, OePNV und Unfallatlas-Daten.

## Inhalt

- [Ueberblick](#ueberblick)
- [Projektstruktur](#projektstruktur)
- [Voraussetzungen](#voraussetzungen)
- [Lokales Setup](#lokales-setup)
- [Umgebungsvariablen](#umgebungsvariablen)
- [Datenquellen und ETL](#datenquellen-und-etl)
- [API](#api)
- [Frontend](#frontend)
- [Datenbank und Persistenz](#datenbank-und-persistenz)
- [Bekannte Besonderheiten](#bekannte-besonderheiten)

## Ueberblick

Das System besteht aus drei Hauptteilen:

1. `apps/backend`
   FastAPI, SQLModel, Alembic und die ETL-Jobs.
2. `apps/frontend`
   Nuxt 3 mit Kartenansichten, Finder, Vergleich und Regions-Detailseiten.
3. `infra`
   Lokale PostGIS-Datenbank per Docker Compose.

Die App arbeitet gemeindescharf, soweit die jeweiligen Quellen das hergeben. Geometrien kommen lokal aus BKG VG25, Demografie aus der Regionalstatistik, OSM-Alltagsnaehe aus `osm2pgsql`, OePNV aus GTFS und Unfallorte aus dem Unfallatlas.

## Projektstruktur

```text
wohnortkompass/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── etl/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── schemas/
│   │   │   └── services/
│   │   ├── migrations/
│   │   ├── pyproject.toml
│   │   └── .env.example
│   └── frontend/
│       ├── components/
│       ├── composables/
│       ├── pages/
│       ├── stores/
│       ├── types/
│       ├── nuxt.config.ts
│       └── .env.example
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
cd wohnortkompass/infra
docker compose up -d
```

Die Datenbank ist danach unter `localhost:5433` verfuegbar.

### 2. Backend einrichten

```bash
cd wohnortkompass/apps/backend
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
cd wohnortkompass/apps/frontend
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

Wichtige Variablen aus `apps/backend/.env.example`:

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

Aus `apps/frontend/.env.example`:

- `NUXT_PUBLIC_API_BASE`
  Basis-URL der API

## Datenquellen und ETL

Die ETL-Jobs sitzen unter `apps/backend/app/etl`.

Typische Reihenfolge:

```bash
cd wohnortkompass/apps/backend
./venv/bin/python -m app.etl.import_bkg
./venv/bin/python -m app.etl.import_destatis
./venv/bin/python -m app.etl.import_dwd
./venv/bin/python -m app.etl.import_uba
./venv/bin/python -m app.etl.import_unfallatlas
./venv/bin/python -m app.etl.import_osm
./venv/bin/python -m app.etl.import_oepnv
./venv/bin/python -m app.etl.build_scores
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

- `apps/frontend/pages/index.vue`
- `apps/frontend/pages/finder.vue`
- `apps/frontend/pages/compare.vue`
- `apps/frontend/pages/methodik.vue`
- `apps/frontend/pages/region/[slug].vue`

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

- Das Repo enthaelt aktuell bereits generierte Artefakte wie `node_modules`, `.nuxt`, `.output`, `venv` und Rohdaten. Eine `.gitignore` sollte diese Verzeichnisse ausschliessen.
- `pnpm-workspace.yaml` verweist derzeit noch auf `apps/web`, waehrend das reale Frontend unter `apps/frontend` liegt.
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
