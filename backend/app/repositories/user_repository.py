from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, user_id: int) -> bool:
        return self._session.scalar(select(User.id).where(User.id == user_id)) is not None

    def list_all(self) -> Sequence[User]:
        return self._session.scalars(select(User).order_by(User.name, User.id)).all()
