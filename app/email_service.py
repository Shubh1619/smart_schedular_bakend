import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def _send_email(email: str, subject: str, body: str, dev_prefix: str) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        print(f"[{dev_prefix}] {email} -> {body}")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [email], msg.as_string())


def send_otp_email(email: str, otp: str) -> None:
    body = f"Your Smart Schedular OTP is: {otp}. It expires in {settings.otp_expire_minutes} minutes."
    _send_email(email, "Smart Schedular OTP Verification", body, "DEV OTP")


def send_team_invite_email(email: str, team_name: str, invite_link: str) -> None:
    body = (
        f"You have been invited to join team '{team_name}' on Smart Schedular.\n\n"
        f"Open this link to join: {invite_link}\n"
    )
    _send_email(email, f"Invitation to join {team_name}", body, "DEV INVITE")


def send_assignment_email(email: str, team_name: str, item_title: str, item_type: str, item_date: str) -> None:
    body = (
        f"You were assigned to a {item_type} in team '{team_name}'.\n\n"
        f"Title: {item_title}\n"
        f"Date: {item_date}\n"
    )
    _send_email(email, f"New {item_type} assignment", body, "DEV ASSIGNMENT")
