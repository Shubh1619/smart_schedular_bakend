from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Assignment, ScheduleItem, TeamMember, User
from app.schemas import AssignUsersRequest, AssignmentOut, MessageResponse, UpdateStatusRequest

router = APIRouter(tags=["Assignment"])


def ensure_team_access(item: ScheduleItem, user_id: int, db: Session):
    membership = db.execute(
        select(TeamMember).where(TeamMember.team_id == item.team_id, TeamMember.user_id == user_id)
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")


@router.post("/assign-users", response_model=list[AssignmentOut])
def assign_users(payload: AssignUsersRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(ScheduleItem, payload.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item, user.id, db)
    if item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can assign users")

    existing = {a.user_id: a for a in item.assignments}
    for user_id in payload.user_ids:
        if user_id not in existing:
            db.add(Assignment(item_id=item.id, user_id=user_id))
    db.commit()
    db.refresh(item)
    return item.assignments


@router.put("/update-status", response_model=AssignmentOut)
def update_status(payload: UpdateStatusRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assignment = db.get(Assignment, payload.assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    item = db.get(ScheduleItem, assignment.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule item missing")
    ensure_team_access(item, user.id, db)
    if assignment.user_id != user.id and item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update status")

    assignment.status = payload.status
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments/{item_id}", response_model=list[AssignmentOut])
def list_assignments(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(ScheduleItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item, user.id, db)
    return item.assignments


@router.delete("/assignments/{assignment_id}", response_model=MessageResponse)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    item = db.get(ScheduleItem, assignment.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item, user.id, db)
    if item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can remove assignment")
    db.delete(assignment)
    db.commit()
    return MessageResponse(message="Assignment removed")

