from datetime import datetime

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    role: str | None = None


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
    count: int


class InviteWorkspaceMemberRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class TransferWorkspaceOwnershipRequest(BaseModel):
    new_owner_user_id: str = Field(min_length=1, max_length=36)


class WorkspaceMembershipResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime
    email: str | None = None


class WorkspaceMembershipListResponse(BaseModel):
    items: list[WorkspaceMembershipResponse]
    count: int


class TransferWorkspaceOwnershipResponse(BaseModel):
    previous_owner: WorkspaceMembershipResponse
    new_owner: WorkspaceMembershipResponse
