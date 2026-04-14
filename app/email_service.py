"""
Email service for sending notifications.
Uses Brevo's Transactional Email API for reliable delivery.
"""
from app.core.email import send_team_invite_email, send_otp_email, send_assignment_email

__all__ = ["send_team_invite_email", "send_otp_email", "send_assignment_email"]

