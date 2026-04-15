import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.core.config import settings


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
) -> bool:
    """
    Send email using Brevo's Transactional Email API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body (optional)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not settings.is_email_configured:
        print(f"[EMAIL] Email not configured properly. Skipping send to {to_email}")
        return False

    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.brevo_api_key

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"name": settings.mail_from_name or "Smart Schedular", "email": settings.smtp_from},
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        api_instance.send_transac_email(email)
        print(f"[EMAIL] ✓ Email sent to {to_email}")
        return True

    except ApiException as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] Unexpected error sending to {to_email}: {e}")
        return False


def send_team_invite_email(to_email: str, team_name: str, team_code: str, invite_link: str) -> bool:
    """Send team invitation email with join code and link."""
    subject = f"Join {team_name} on Smart Schedular 🎉"
    
    html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 12px; padding: 32px; color: white; text-align: center;">
                <h1 style="margin: 0 0 16px 0; font-size: 28px;">You're Invited! 🎉</h1>
                <p style="margin: 0; font-size: 16px; opacity: 0.95;">Join <strong>{team_name}</strong> and start collaborating</p>
            </div>
            
            <div style="padding: 32px 0; text-align: center;">
                <p style="font-size: 16px; color: #374151; line-height: 1.6; margin: 0 0 24px 0;">
                    You have been invited to join the team <strong>{team_name}</strong>. 
                </p>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{invite_link}" style="
                        display: inline-block;
                        background: #4F46E5;
                        color: white;
                        padding: 14px 40px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                        transition: background 0.2s;
                    ">Accept Invite</a>
                </div>
                
                <p style="font-size: 14px; color: #6B7280; line-height: 1.6; margin-top: 24px;">
                    Or enter this code manually in your dashboard:
                </p>
                
                <div style="
                    background: #F3F4F6;
                    border: 2px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 16px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 32px;
                    font-weight: 700;
                    color: #4F46E5;
                    letter-spacing: 4px;
                ">{team_code}</div>
            </div>
            
            <div style="text-align: center; padding-top: 24px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #9CA3AF;">
                <p style="margin: 0;">© 2026 Smart Schedular. All rights reserved.</p>
            </div>
        </div>
    """
    
    text_content = f"""
You're Invited! 🎉

You have been invited to join the team "{team_name}" on Smart Schedular.

Accept Invite Link: {invite_link}
Or enter this code manually in your dashboard: {team_code}

© 2026 Smart Schedular
    """
    
    return send_email(to_email, subject, html_content, text_content)


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP verification email."""
    subject = f"Your Smart Schedular OTP: {otp}"
    
    html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 12px; padding: 32px; color: white; text-align: center;">
                <h1 style="margin: 0 0 16px 0; font-size: 28px;">Verify Your Email</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.95;">Enter this code to verify your account</p>
            </div>
            
            <div style="padding: 32px 0; text-align: center;">
                <div style="
                    background: #F3F4F6;
                    border: 2px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 24px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 32px;
                    font-weight: 700;
                    color: #4F46E5;
                    letter-spacing: 4px;
                ">{otp}</div>
                
                <p style="font-size: 14px; color: #6B7280; margin: 0;">
                    This code expires in <strong>{settings.otp_expire_minutes} minutes</strong>
                </p>
                
                <p style="font-size: 13px; color: #9CA3AF; margin-top: 24px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    If you didn't request this code, please ignore this email.
                </p>
            </div>
        </div>
    """
    
    text_content = f"""
Verify Your Email

Enter this code to verify your account:

{otp}

This code expires in {settings.otp_expire_minutes} minutes.

If you didn't request this code, please ignore this email.
    """
    
    return send_email(to_email, subject, html_content, text_content)


def send_assignment_email(
    to_email: str,
    team_name: str,
    item_title: str,
    item_type: str,
    item_date: str,
) -> bool:
    """Send assignment notification email."""
    subject = f"New {item_type.title()} Assignment in {team_name}"
    
    html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 12px; padding: 24px; color: white;">
                <h2 style="margin: 0; font-size: 22px;">New {item_type.title()} Assigned</h2>
                <p style="margin: 8px 0 0 0; opacity: 0.95; font-size: 14px;">in <strong>{team_name}</strong></p>
            </div>
            
            <div style="padding: 32px 0;">
                <div style="background: #F9FAFB; border-left: 4px solid #4F46E5; padding: 16px; margin: 24px 0; border-radius: 4px;">
                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;">
                        {item_type.title()}
                    </p>
                    <h3 style="margin: 0 0 8px 0; font-size: 18px; color: #1F2937;">
                        {item_title}
                    </h3>
                    <p style="margin: 0; font-size: 14px; color: #6B7280;">
                        📅 {item_date}
                    </p>
                </div>
                
                <p style="font-size: 14px; color: #6B7280; line-height: 1.6; margin: 24px 0;">
                    You have been assigned to a new <strong>{item_type}</strong> in <strong>{team_name}</strong>. 
                    Log in to Smart Schedular to view more details and update the status.
                </p>
            </div>
            
            <div style="text-align: center; padding-top: 24px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #9CA3AF;">
                <p style="margin: 0;">© 2026 Smart Schedular. All rights reserved.</p>
            </div>
        </div>
    """
    
    text_content = f"""
New {item_type.title()} Assigned

You have been assigned to a new {item_type}:

Title: {item_title}
Team: {team_name}
Date: {item_date}

Log in to Smart Schedular to view more details and update the status.

© 2026 Smart Schedular
    """
    
    return send_email(to_email, subject, html_content, text_content)
