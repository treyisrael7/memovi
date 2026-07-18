from datetime import datetime

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_at: datetime


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
    count: int
