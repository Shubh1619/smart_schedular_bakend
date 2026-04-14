from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Attachment, ScheduleItem, TeamMember, User
from app.schemas import AddAttachmentRequest, AttachmentOut, MessageResponse

router = APIRouter(tags=["Attachments"])


def ensure_team_access(item: ScheduleItem, user_id: int, db: Session):
    membership = db.execute(
        select(TeamMember).where(TeamMember.team_id == item.team_id, TeamMember.user_id == user_id)
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")


@router.post("/add-attachment", response_model=AttachmentOut)
def add_attachment(payload: AddAttachmentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(ScheduleItem, payload.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item, user.id, db)
    if item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can add attachment")

    attachment = Attachment(item_id=item.id, url=str(payload.url), label=payload.label)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/attachments/{item_id}", response_model=list[AttachmentOut])
def get_attachments(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(ScheduleItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    ensure_team_access(item, user.id, db)
    return item.attachments


@router.delete("/attachments/{attachment_id}", response_model=MessageResponse)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    item = db.get(ScheduleItem, attachment.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item missing")
    ensure_team_access(item, user.id, db)
    if item.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can delete attachment")
    db.delete(attachment)
    db.commit()
    return MessageResponse(message="Attachment deleted")

