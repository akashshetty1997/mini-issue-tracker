from fastapi import APIRouter

from app.api.deps import UserDirectoryDep
from app.api.rate_limit import ReadRateLimit
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"], dependencies=[ReadRateLimit])


# Read-only with no business rules, so this goes straight to the repository.
@router.get("", summary="List users who can be assigned issues")
def list_users(users: UserDirectoryDep) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in users.list_all()]
