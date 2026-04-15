import sys
from app.core.email import send_team_invite_email

try:
    success = send_team_invite_email("test@example.com", "Test Team", "http://example.com/join")
    print(f"Success: {success}")
except Exception as e:
    print(f"Exception: {e}")
