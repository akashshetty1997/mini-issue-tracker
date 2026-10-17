from fastapi import APIRouter

from app.api.rate_limit import ReadRateLimit
from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    DESCRIPTION_MAX_LENGTH,
    MAX_PAGE_SIZE,
    SEARCH_MAX_LENGTH,
    SORTABLE_FIELDS,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    IssuePriority,
    IssueStatus,
)
from app.schemas.meta import FieldLimits, MetaRead
from app.services.status_policy import DEFAULT_STATUS_POLICY

router = APIRouter(prefix="/meta", tags=["meta"], dependencies=[ReadRateLimit])


@router.get("", summary="Statuses, priorities, transitions and field limits")
def get_meta() -> MetaRead:
    return MetaRead(
        statuses=list(IssueStatus),
        priorities=list(IssuePriority),
        status_transitions={
            status: DEFAULT_STATUS_POLICY.allowed_from(status) for status in IssueStatus
        },
        limits=FieldLimits(
            title_min_length=TITLE_MIN_LENGTH,
            title_max_length=TITLE_MAX_LENGTH,
            description_max_length=DESCRIPTION_MAX_LENGTH,
            default_page_size=DEFAULT_PAGE_SIZE,
            max_page_size=MAX_PAGE_SIZE,
            search_max_length=SEARCH_MAX_LENGTH,
        ),
        sortable_fields=list(SORTABLE_FIELDS),
        default_sort=DEFAULT_SORT,
    )
