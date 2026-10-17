from pydantic import BaseModel, ConfigDict


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserRead(UserSummary):
    email: str
