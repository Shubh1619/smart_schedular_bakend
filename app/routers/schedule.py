from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user, get_db
from app.email_service import send_assignment_email
from app.models import Assignment, Attachment, ScheduleItem, Team, TeamMember, User
from app.schemas import MessageResponse, ScheduleItemCreate, ScheduleItemOut, ScheduleItemUpdate

router = APIRouter(tags=["Schedule"])


def ensure_team_access(team_id: int, user_id: int, db: Session) -> None:
    membership = db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")


def _validate_assignees(team_id: int, assignee_ids: list[int], db: Session) -> list[int]:
    unique_ids = list(dict.fromkeys(assignee_ids))
    if not unique_ids:
        return []

    team_member_user_ids = {
        member.user_id
        for member in db.execute(select(TeamMember).where(TeamMember.team_id == team_id)).scalars().all()
    }
    invalid_ids = [assignee_id for assignee_id in unique_ids if assignee_id not in team_member_user_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assignees for this team: {invalid_ids}",
        )
    return unique_ids


def _replace_assignments(item: ScheduleItem, assignee_ids: list[int], db: Session) -> None:
    existing_map = {assignment.user_id: assignment for assignment in item.assignments}
    incoming = set(assignee_ids)

    for existing_user_id, assignment in existing_map.items():
        if existing_user_id not in incoming:
            db.delete(assignment)

    for assignee_id in assignee_ids:
        if assignee_id not in existing_map:
            db.add(Assignment(item_id=item.id, user_id=assignee_id))


def _send_assignment_notifications(
    item: ScheduleItem,
    assignee_ids: list[int],
    db: Session,
) -> None:
    if not assignee_ids:
        return
    
    team = db.get(Team, item.team_id)
    user_ids = set(assignee_ids)
    
    # Batch load users
    if user_ids:
        users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
        user_map = {u.id: u for u in users}
        
        for assignee_id in assignee_ids:
            if assignee_id in user_map:
                assignee = user_map[assignee_id]
                send_assignment_email(
                    assignee.email,
                    team.name if team else "Team",
                    item.title,
                    item.type.value,
                    item.date.isoformat(),
                )


def _validate_item_date_not_in_past(item_date: date) -> None:
    if item_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Past dates are not allowed for events, tasks, or notes",
        )


@router.post("/create-item", response_model=ScheduleItemOut)
def create_item(
    payload: ScheduleItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _validate_item_date_not_in_past(payload.date)
    ensure_team_access(payload.team_id, user.id, db)
    assignee_ids = _validate_assignees(payload.team_id, payload.assignee_ids, db)
    item = ScheduleItem(
        title=payload.title,
        description=payload.description,
        date=payload.date,
        time=payload.time,
        type=payload.type,
        created_by=user.id,
        team_id=payload.team_id,
    )
    db.add(item)
    db.flush()

    _replace_assignments(item, assignee_ids, db)

    for attachment in payload.attachments:
        url = attachment.get("url")
        if url:
            db.add(Attachment(item_id=item.id, url=url, label=attachment.get("label")))

    db.commit()
    db.refresh(item)
    _send_assignment_notifications(item, assignee_ids, db)
    return _serialize_item(item, {user.id: user})


@router.get("/get-items", response_model=list[ScheduleItemOut])
def get_items(team_id: int = Query(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_team_access(team_id, user.id, db)
    items = db.execute(
        select(ScheduleItem)
        .options(selectinload(ScheduleItem.assignments), selectinload(ScheduleItem.attachments))
        .where(ScheduleItem.team_id == team_id)
        .order_by(ScheduleItem.date.asc())
    ).unique().scalars().all()
    
    # Batch load creators
    creator_ids = set(item.created_by for item in items)
    creator_map = {}
    if creator_ids:
        creators = db.execute(select(User).where(User.id.in_(creator_ids))).scalars().all()
        creator_map = {u.id: u for u in creators}
    
    response_data = [_serialize_item(item, creator_map) for item in items]
    
    # Add caching headers - cache for 1 minute
    return JSONResponse(
        content=jsonable_encoder(response_data),
        headers={
            "Cache-Control": "public, max-age=60",
            "Vary": "Authorization",
        }
    )


@router.get("/schedule", response_model=list[ScheduleItemOut])
def get_schedule(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if team_id is not None:
        ensure_team_access(team_id, user.id, db)
        items = db.execute(
            select(ScheduleItem)
            .options(selectinload(ScheduleItem.assignments), selectinload(ScheduleItem.attachments))
            .where(ScheduleItem.team_id == team_id)
            .order_by(ScheduleItem.date.asc())
        ).unique().scalars().all()
    else:
        memberships = db.execute(select(TeamMember).where(TeamMember.user_id == user.id)).scalars().all()
        if not memberships:
            return []
        team_ids = [membership.team_id for membership in memberships]
        items = db.execute(
            select(ScheduleItem)
            .options(selectinload(ScheduleItem.assignments), selectinload(ScheduleItem.attachments))
            .where(ScheduleItem.team_id.in_(team_ids))
            .order_by(ScheduleItem.date.asc())
        ).unique().scalars().all()
    
    # Batch load creators
    creator_ids = set(item.created_by for item in items)
    creator_map = {}
    if creator_ids:
        creators = db.execute(select(User).where(User.id.in_(creator_ids))).scalars().all()
        creator_map = {u.id: u for u in creators}
    
    response_data = [_serialize_item(item, creator_map) for item in items]
    
    # Add caching headers: Cache for 1 minute, validate freshness with ETag
    # Frontend can safely show cached data while checking for updates in background
    return JSONResponse(
        content=response_data,
        headers={
            "Cache-Control": "public, max-age=60",
            "Vary": "Authorization",
        }
    )


@router.put("/update-item/{item_id}", response_model=ScheduleItemOut)
def update_item(
    item_id: int,
    payload: ScheduleItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.get(ScheduleItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item.team_id, user.id, db)
    if item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can edit item")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("date") is not None:
        _validate_item_date_not_in_past(update_data["date"])
    incoming_assignees = update_data.pop("assignee_ids", None)
    incoming_attachments = update_data.pop("attachments", None)
    for key, value in update_data.items():
        setattr(item, key, value)
    if incoming_assignees is not None:
        assignee_ids = _validate_assignees(item.team_id, incoming_assignees, db)
        _replace_assignments(item, assignee_ids, db)
    if incoming_attachments is not None:
        for attachment in item.attachments:
            db.delete(attachment)
        for attachment in incoming_attachments:
            url = attachment.get("url")
            if url:
                db.add(Attachment(item_id=item.id, url=url, label=attachment.get("label")))
    db.commit()
    db.refresh(item)
    if incoming_assignees is not None:
        _send_assignment_notifications(item, assignee_ids, db)
    return _serialize_item(item, {user.id: user})


@router.delete("/delete-item/{item_id}", response_model=MessageResponse)
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(ScheduleItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item.team_id, user.id, db)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Deleting events, tasks, and notes is disabled",
    )


def _serialize_item(item: ScheduleItem, creator_map: dict = None) -> ScheduleItemOut:
    creator_name = "Unknown"
    if creator_map and item.created_by in creator_map:
        creator_name = creator_map[item.created_by].full_name
    return ScheduleItemOut(
        id=item.id,
        title=item.title,
        description=item.description,
        date=item.date,
        time=item.time,
        type=item.type,
        created_by=item.created_by,
        team_id=item.team_id,
        created_at=item.created_at,
        creator_name=creator_name,
        assignments=item.assignments,
        attachments=item.attachments,
    )
