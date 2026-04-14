from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.models import AssignmentStatus, ItemType, RoleEnum


class MessageResponse(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=10)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: int
    email: str
    full_name: str


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    participant_emails: list[EmailStr] = Field(default_factory=list)


class JoinTeamRequest(BaseModel):
    code: str


class InviteMemberRequest(BaseModel):
    team_id: int
    emails: list[EmailStr] = Field(min_items=1)


class TeamUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class TeamMemberOut(BaseModel):
    id: int
    user_id: int
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)


class TeamOut(BaseModel):
    id: int
    name: str
    code: str
    owner_id: int
    invite_token: Optional[str] = None
    members: list[TeamMemberOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ScheduleItemCreate(BaseModel):
    team_id: int
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    date: date
    time: Optional[time] = None
    type: ItemType
    assignee_ids: list[int] = Field(default_factory=list)
    attachments: list[dict[str, str]] = Field(default_factory=list)


class ScheduleItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    type: Optional[ItemType] = None
    assignee_ids: Optional[list[int]] = None
    attachments: Optional[list[dict[str, str]]] = None


class AssignmentOut(BaseModel):
    id: int
    item_id: int
    user_id: int
    status: AssignmentStatus

    model_config = ConfigDict(from_attributes=True)


class AttachmentOut(BaseModel):
    id: int
    item_id: int
    url: str
    label: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    date: date
    time: Optional[time]
    type: ItemType
    created_by: int
    team_id: int
    created_at: datetime
    creator_name: str
    assignments: list[AssignmentOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignUsersRequest(BaseModel):
    item_id: int
    user_ids: list[int]


class UpdateStatusRequest(BaseModel):
    assignment_id: int
    status: AssignmentStatus


class AddAttachmentRequest(BaseModel):
    item_id: int
    url: HttpUrl
    label: Optional[str] = Field(default=None, max_length=200)


class ProfileOut(BaseModel):
    user_id: int
    email: str
    full_name: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
