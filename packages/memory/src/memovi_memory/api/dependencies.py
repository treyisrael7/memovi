from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession


def get_database_session() -> OrmSession:
    raise RuntimeError("Memory database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]
