from fastapi import APIRouter

from app.api.v1 import issues, meta, users
from app.schemas.common import ErrorResponse

# Every v1 endpoint can fail validation or hit an unexpected error; document the envelope.
router = APIRouter(
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Unexpected error"},
    }
)
router.include_router(issues.router)
router.include_router(users.router)
router.include_router(meta.router)
