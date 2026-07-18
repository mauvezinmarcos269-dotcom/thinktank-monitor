from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.think_tank import OrganizationTypeEnum


class ThinkTankBase(BaseModel):

    name: str

    name_en: str | None = None

    country: str

    website: str | None = None

    description: str | None = None

    organization_type: OrganizationTypeEnum = (
        OrganizationTypeEnum.think_tank
    )

    parent_id: int | None = None

    is_key: bool = False



class ThinkTankCreate(ThinkTankBase):
    pass



class ThinkTankUpdate(BaseModel):

    name: str | None = None

    website: str | None = None

    description: str | None = None

    is_active: bool | None = None



class ThinkTankResponse(ThinkTankBase):

    id: int

    is_active: bool

    created_at: datetime

    updated_at: datetime


    model_config = ConfigDict(
        from_attributes=True
    )
