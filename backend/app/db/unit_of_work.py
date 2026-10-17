from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.errors import translate_integrity_error


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Discard anything not explicitly committed (a no-op after a successful commit).
        self._session.rollback()
        if isinstance(exc, IntegrityError):
            domain_error = translate_integrity_error(exc)
            if domain_error is not None:
                raise domain_error from exc

    def commit(self) -> None:
        self._session.commit()
