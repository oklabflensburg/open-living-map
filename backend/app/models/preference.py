from datetime import datetime

from sqlmodel import Field, SQLModel


class UserPreferenceSession(SQLModel, table=True):
    __tablename__ = "user_preference_session"

    id: int | None = Field(default=None, primary_key=True)
    climate_weight: int = 0
    air_weight: int = 0
    safety_weight: int = 0
    demographics_weight: int = 0
    amenities_weight: int = 0
    oepnv_weight: int = 0
    urban_preference: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
