import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.deps import get_current_user, get_db
from app.email_service import send_team_invite_email
from app.models import RoleEnum, ScheduleItem, Team, TeamMember, User
from app.schemas import InviteMemberRequest, JoinTeamRequest, MessageResponse, TeamCreateRequest, TeamOut, TeamUpdateRequest

router = APIRouter(tags=["Team"])


def generate_team_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_team_member(team_id: int, user_id: int, db: Session) -> TeamMember:
    membership = db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")
    return membership


def ensure_team_owner(team_id: int, user_id: int, db: Session) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if team.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owner can perform this action")
    return team


def build_invite_link(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/join?token={token}"


@router.post("/create-team", response_model=TeamOut)
def create_team(payload: TeamCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    code = generate_team_code()
    invite_token = secrets.token_urlsafe(24)
    while db.execute(select(Team).where(Team.code == code)).scalar_one_or_none():
        code = generate_team_code()

    team = Team(name=payload.name, code=code, owner_id=user.id, invite_token=invite_token)
    db.add(team)
    db.flush()

    member = TeamMember(user_id=user.id, team_id=team.id, role=RoleEnum.owner)
    db.add(member)
    db.commit()
    db.refresh(team)

    invite_link = build_invite_link(team.invite_token or "")
    for email in payload.participant_emails:
        if email.lower() == user.email.lower():
            continue
        send_team_invite_email(str(email), team.name, invite_link)

    return team


@router.post("/join-team", response_model=MessageResponse)
def join_team(payload: JoinTeamRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    team = db.execute(select(Team).where(Team.code == payload.code.upper())).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    existing = db.execute(
        select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        return MessageResponse(message="Already joined this team")

    db.add(TeamMember(user_id=user.id, team_id=team.id, role=RoleEnum.member))
    db.commit()
    return MessageResponse(message="Joined team successfully")


@router.get("/join-team", response_model=MessageResponse)
def join_team_by_link(token: str = Query(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    team = db.execute(select(Team).where(Team.invite_token == token)).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite link invalid")
    existing = db.execute(
        select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        return MessageResponse(message="Already joined this team")

    db.add(TeamMember(user_id=user.id, team_id=team.id, role=RoleEnum.member))
    db.commit()
    return MessageResponse(message="Joined team successfully via invite link")


@router.post("/invite-member", response_model=MessageResponse)
def invite_member(payload: InviteMemberRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    team = ensure_team_owner(payload.team_id, user.id, db)
    invite_link = build_invite_link(team.invite_token or "")
    send_team_invite_email(str(payload.email), team.name, invite_link)
    return MessageResponse(message=f"Invite sent to {payload.email}")


@router.get("/teams", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    memberships = db.execute(select(TeamMember).where(TeamMember.user_id == user.id)).scalars().all()
    if not memberships:
        return []
    team_ids = [m.team_id for m in memberships]
    return db.execute(select(Team).where(Team.id.in_(team_ids))).scalars().all()


@router.get("/teams/{team_id}/members")
def list_members(team_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_team_member(team_id, user.id, db)
    rows = db.execute(select(TeamMember, User).join(User, User.id == TeamMember.user_id).where(TeamMember.team_id == team_id)).all()
    return [
        {"user_id": tm.user_id, "role": tm.role, "email": u.email, "full_name": u.full_name}
        for tm, u in rows
    ]


@router.put("/teams/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    team = ensure_team_owner(team_id, user.id, db)
    team.name = payload.name
    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", response_model=MessageResponse)
def delete_team(team_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    team = ensure_team_owner(team_id, user.id, db)
    team_items = db.execute(select(ScheduleItem).where(ScheduleItem.team_id == team_id)).scalars().all()
    for item in team_items:
        db.delete(item)
    team_members = db.execute(select(TeamMember).where(TeamMember.team_id == team_id)).scalars().all()
    for member in team_members:
        db.delete(member)
    db.delete(team)
    db.commit()
    return MessageResponse(message="Team deleted")


@router.delete("/teams/{team_id}/members/{member_user_id}", response_model=MessageResponse)
def remove_member(
    team_id: int,
    member_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    team = ensure_team_owner(team_id, user.id, db)
    if member_user_id == team.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be removed")

    member = db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == member_user_id)
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    db.delete(member)
    db.commit()
    return MessageResponse(message="Member removed")
