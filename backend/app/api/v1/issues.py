"""HTTP layer for issues: translate requests to service calls and results to responses."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, Response

from app.api.deps import IssueServiceDep
from app.api.rate_limit import ReadRateLimit, WriteRateLimit
from app.core.constants import MAX_DB_INT
from app.schemas.common import ErrorResponse, Page
from app.schemas.issue import IssueCreate, IssueListParams, IssueRead, IssueUpdate

router = APIRouter(prefix="/issues", tags=["issues"])

IssueId = Annotated[int, Path(gt=0, le=MAX_DB_INT, description="Issue id")]

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Issue not found"}
}
CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {"model": ErrorResponse, "description": "Invalid status transition"}
}


@router.get("", summary="List issues", dependencies=[ReadRateLimit])
def list_issues(
    service: IssueServiceDep, params: Annotated[IssueListParams, Query()]
) -> Page[IssueRead]:
    result = service.list_issues(params.filters(), params.sort_order(), params.page_request())
    return Page[IssueRead](
        items=[IssueRead.model_validate(issue) for issue in result.items],
        total=result.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.post("", status_code=201, summary="Create an issue", dependencies=[WriteRateLimit])
def create_issue(
    data: IssueCreate, service: IssueServiceDep, request: Request, response: Response
) -> IssueRead:
    issue = service.create_issue(data)
    response.headers["Location"] = request.url_for("get_issue", issue_id=issue.id).path
    return IssueRead.model_validate(issue)


@router.get(
    "/{issue_id}",
    name="get_issue",
    summary="Get an issue",
    responses=NOT_FOUND,
    dependencies=[ReadRateLimit],
)
def get_issue(issue_id: IssueId, service: IssueServiceDep) -> IssueRead:
    return IssueRead.model_validate(service.get_issue(issue_id))


@router.patch(
    "/{issue_id}",
    summary="Update an issue (partial)",
    responses={**NOT_FOUND, **CONFLICT},
    dependencies=[WriteRateLimit],
)
def update_issue(issue_id: IssueId, data: IssueUpdate, service: IssueServiceDep) -> IssueRead:
    return IssueRead.model_validate(service.update_issue(issue_id, data))


@router.delete(
    "/{issue_id}",
    status_code=204,
    response_class=Response,
    summary="Delete an issue",
    responses=NOT_FOUND,
    dependencies=[WriteRateLimit],
)
def delete_issue(issue_id: IssueId, service: IssueServiceDep) -> None:
    service.delete_issue(issue_id)
