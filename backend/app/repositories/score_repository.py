import re

from sqlalchemy import desc
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.ars import lookup_candidates, to_district_code
from app.core.config import settings
from app.models.indicator import IndicatorDefinition
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot


DISTRICT_NAME_COLUMNS = [
    "gen_krs",
    "krs_name",
    "kreis_name",
    "landkreis",
    "name_krs",
    "gen_kreis",
    "kreis",
    "bez_krs",
]

DISTRICT_CODE_COLUMNS = [
    "ags",
    "ars",
]

CATEGORY_SCORE_COLUMNS = {
    "climate": "score_climate",
    "air": "score_air",
    "safety": "score_safety",
    "demographics": "score_demographics",
    "amenities": "score_amenities",
    "oepnv": "score_oepnv",
}


def _qualified_table_name(value: str) -> tuple[str, str]:
    normalized = value.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", normalized):
        raise ValueError(f"Ungueltiger SQL-Identifier: {value}")
    if "." in normalized:
        schema, table = normalized.split(".", 1)
    else:
        schema, table = "public", normalized
    return schema, table


def _paired_district_table_name(table: str) -> str | None:
    if table.endswith("_gem"):
        return table[:-4] + "_krs"
    return None


class ScoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_indicators(self) -> list[IndicatorDefinition]:
        statement = select(IndicatorDefinition).order_by(IndicatorDefinition.category, IndicatorDefinition.key)
        return list(self.session.exec(statement))

    def list_snapshots(
        self,
        include_ars: list[str] | None = None,
        state_code: str | None = None,
    ) -> list[tuple[Region, RegionScoreSnapshot]]:
        statement = (
            select(Region, RegionScoreSnapshot)
            .join(RegionScoreSnapshot, Region.id == RegionScoreSnapshot.region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
        )
        if include_ars:
            candidates: set[str] = set()
            for item in include_ars:
                candidates.update(lookup_candidates(item))
            statement = statement.where(Region.ars.in_(list(candidates)))
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        return list(self.session.exec(statement).all())

    def list_indicator_values(self, region_id: int) -> list[tuple[IndicatorDefinition, RegionIndicatorValue]]:
        statement = (
            select(IndicatorDefinition, RegionIndicatorValue)
            .join(RegionIndicatorValue, RegionIndicatorValue.indicator_id == IndicatorDefinition.id)
            .where(RegionIndicatorValue.region_id == region_id)
            .where(RegionIndicatorValue.period == settings.default_score_period)
            .order_by(IndicatorDefinition.category, IndicatorDefinition.key)
        )
        return list(self.session.exec(statement).all())

    def list_top_snapshots_by_category(
        self,
        *,
        category: str,
        state_code: str | None = None,
        limit: int = 100,
    ) -> list[tuple[Region, RegionScoreSnapshot]]:
        score_column_name = CATEGORY_SCORE_COLUMNS.get(category)
        if score_column_name is None:
            raise ValueError(f"Unknown ranking category: {category}")

        score_column = getattr(RegionScoreSnapshot, score_column_name)
        statement = (
            select(Region, RegionScoreSnapshot)
            .join(RegionScoreSnapshot, Region.id == RegionScoreSnapshot.region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
            .order_by(desc(score_column), Region.id)
            .limit(limit)
        )
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        return list(self.session.exec(statement).all())

    def resolve_district_name(self, ars: str) -> str | None:
        try:
            schema, table = _qualified_table_name(settings.bkg_municipality_table)
        except ValueError:
            return None

        columns = {
            str(row[0])
            for row in self.session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = :table
                    """
                ),
                {"schema": schema, "table": table},
            ).all()
        }
        district_column = next((column for column in DISTRICT_NAME_COLUMNS if column in columns), None)
        if district_column is None:
            return None

        row = self.session.execute(
            text(
                f"""
                SELECT {district_column}
                FROM {schema}.{table}
                WHERE ags = :ars
                LIMIT 1
                """
            ),
            {"ars": ars},
        ).first()
        if row is None or row[0] in (None, ""):
            district_name = None
        else:
            district_name = str(row[0]).strip() or None
        if district_name:
            return district_name

        if not {"sn_l", "sn_k"}.issubset(columns):
            return None

        district_table = _paired_district_table_name(table)
        if district_table is None:
            return None

        district_table_exists = self.session.execute(
            text("SELECT to_regclass(:qualified_name) IS NOT NULL"),
            {"qualified_name": f"{schema}.{district_table}"},
        ).scalar()
        if not district_table_exists:
            return None

        district_columns = {
            str(result[0])
            for result in self.session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = :table
                    """
                ),
                {"schema": schema, "table": district_table},
            ).all()
        }
        if not {"gen", "sn_l", "sn_k"}.issubset(district_columns):
            district_name_column = "gen" if "gen" in district_columns else next(
                (column for column in DISTRICT_NAME_COLUMNS if column in district_columns),
                None,
            )
            district_code_column = next(
                (column for column in DISTRICT_CODE_COLUMNS if column in district_columns),
                None,
            )
            if district_name_column and district_code_column:
                district_code = to_district_code(ars)
                if not district_code:
                    return None
                row = self.session.execute(
                    text(
                        f"""
                        SELECT {district_name_column}
                        FROM {schema}.{district_table}
                        WHERE LEFT({district_code_column}::text, 5) = :district_code
                        ORDER BY {district_name_column}
                        LIMIT 1
                        """
                    ),
                    {"district_code": district_code},
                ).first()
                if row is None or row[0] in (None, ""):
                    return None
                return str(row[0]).strip() or None
            return None

        has_regional_key = "sn_r" in columns and "sn_r" in district_columns
        gf_order = "CASE WHEN k.gf = :preferred_gf THEN 0 ELSE 1 END, " if "gf" in district_columns else ""
        join_regional_key = "AND COALESCE(k.sn_r, 0) = COALESCE(g.sn_r, 0)" if has_regional_key else ""
        row = self.session.execute(
            text(
                f"""
                SELECT k.gen
                FROM {schema}.{table} g
                JOIN {schema}.{district_table} k
                  ON k.sn_l = g.sn_l
                 AND k.sn_k = g.sn_k
                 {join_regional_key}
                WHERE g.ags = :ars
                ORDER BY {gf_order} k.gen
                LIMIT 1
                """
            ),
            {"ars": ars, "preferred_gf": settings.bkg_geometry_flavour},
        ).first()
        if row is not None and row[0] not in (None, ""):
            return str(row[0]).strip() or None

        district_name_column = "gen" if "gen" in district_columns else next(
            (column for column in DISTRICT_NAME_COLUMNS if column in district_columns),
            None,
        )
        district_code_column = next(
            (column for column in DISTRICT_CODE_COLUMNS if column in district_columns),
            None,
        )
        if district_name_column and district_code_column:
            district_code = to_district_code(ars)
            if not district_code:
                return None
            row = self.session.execute(
                text(
                    f"""
                    SELECT {district_name_column}
                    FROM {schema}.{district_table}
                    WHERE LEFT({district_code_column}::text, 5) = :district_code
                    ORDER BY {district_name_column}
                    LIMIT 1
                    """
                ),
                {"district_code": district_code},
            ).first()
            if row is not None and row[0] not in (None, ""):
                return str(row[0]).strip() or None
        return None

    def list_amenity_aggregates(self, ars: str) -> list[tuple[str, int, float]]:
        table_exists = self.session.execute(text("SELECT to_regclass('osm.region_amenity_agg') IS NOT NULL")).scalar()
        if not table_exists:
            return []

        rows = self.session.execute(
            text(
                """
                SELECT category, count_total, per_10k::float
                FROM osm.region_amenity_agg
                WHERE ars = :ars
                ORDER BY category
                """
            ),
            {"ars": ars},
        ).all()
        return [(str(row[0]), int(row[1]), float(row[2])) for row in rows]
