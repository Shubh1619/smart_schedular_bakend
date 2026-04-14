import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user, get_db
from app.email_service import send_otp_email
from app.models import OTPCode, Assignment, ScheduleItem, Team, TeamMember, User
from app.schemas import LoginRequest, MessageResponse, ProfileOut, ProfileUpdateRequest, RegisterRequest, TokenResponse, VerifyOTPRequest

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=MessageResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing and existing.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    if not existing:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            is_verified=False,
        )
        db.add(user)
    else:
        existing.full_name = payload.full_name
        existing.hashed_password = hash_password(payload.password)
        existing.is_verified = False

    otp = f"{random.randint(100000, 999999)}"
    otp_row = OTPCode(
        email=payload.email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes),
        used=False,
    )
    db.add(otp_row)
    db.commit()
    send_otp_email(payload.email, otp)
    return MessageResponse(message="OTP sent to email")


@router.post("/verify-otp", response_model=MessageResponse)
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_row = db.execute(
        select(OTPCode).where(OTPCode.email == payload.email).order_by(desc(OTPCode.id))
    ).scalar_one_or_none()
    if not otp_row or otp_row.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")
    if otp_row.otp != payload.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect OTP")
    if otp_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")

    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_row.used = True
    user.is_verified = True
    db.commit()
    return MessageResponse(message="Account verified successfully")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email. Please register first.",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please check your password and try again.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify OTP before logging in.",
        )

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return ProfileOut(user_id=user.id, email=user.email, full_name=user.full_name)


@router.put("/profile", response_model=TokenResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.email and payload.email != user.email:
        existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if existing and existing.id != user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        user.email = str(payload.email)

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


@router.delete("/profile", response_model=MessageResponse)
def delete_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    memberships = db.execute(select(TeamMember).where(TeamMember.user_id == user.id)).scalars().all()
    owned_team_ids = {team.id for team in db.execute(select(Team).where(Team.owner_id == user.id)).scalars().all()}

    for team_id in owned_team_ids:
        team_items = db.execute(select(ScheduleItem).where(ScheduleItem.team_id == team_id)).scalars().all()
        for item in team_items:
            db.delete(item)

        team_members = db.execute(select(TeamMember).where(TeamMember.team_id == team_id)).scalars().all()
        for member in team_members:
            db.delete(member)

        team = db.get(Team, team_id)
        if team:
            db.delete(team)

    user_items = db.execute(select(ScheduleItem).where(ScheduleItem.created_by == user.id)).scalars().all()
    for item in user_items:
        db.delete(item)

    assignments = db.execute(select(Assignment).where(Assignment.user_id == user.id)).scalars().all()
    for assignment in assignments:
        db.delete(assignment)

    for membership in memberships:
        existing = db.get(TeamMember, membership.id)
        if existing:
            db.delete(existing)

    otps = db.execute(select(OTPCode).where(OTPCode.email == user.email)).scalars().all()
    for otp in otps:
        db.delete(otp)

    db.delete(user)
    db.commit()
    return MessageResponse(message="Profile deleted successfully")
