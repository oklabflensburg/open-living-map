from pydantic import BaseModel, ConfigDict


class IndicatorMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    category: str
    unit: str
    direction: str
    source_name: str
    source_url: str
    methodology: str


class IndicatorMetadataResponse(BaseModel):
    items: list[IndicatorMetadata]
