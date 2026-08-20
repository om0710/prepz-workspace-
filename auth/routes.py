from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta, datetime
import logging

from database import get_user_by_email, create_user, update_user_activity, get_email_logs, log_user_activity
from services.google_auth_service import google_auth_service
from services.email_service import email_service
from services.jwt_service import jwt_service

logger = logging.getLogger("auth_router")

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Google ID Token or Access Token from GIS")

class GoogleLoginResponse(BaseModel):
    status: str
    access_token: str
    user: dict
    email_sent: bool = True
    message: str = "Google login successful"

@router.post("/google-login", response_model=GoogleLoginResponse)
async def google_login(request: GoogleLoginRequest):
    """
    Google Sign-In Endpoint:
    1. Verify Google ID / Access token with Google OAuth servers
    2. Retrieve or create user record in Prepz database
    3. Automatically send welcome email notification to student's Gmail
    4. Generate JWT access token and return authenticated payload
    """
    try:
        # Step 1: Verify token
        google_user = await google_auth_service.verify_google_token_async(request.id_token)
        email = google_user["email"]
        name = google_user.get("name") or email.split("@")[0].title()
        picture = google_user.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
        google_id = google_user.get("google_id")

        logger.info(f"Google auth verified for student: {email}")

        # Step 2: Database lookup / creation
        user = get_user_by_email(email)
        is_new_user = False

        if not user:
            user = create_user(
                name=name,
                email=email,
                password=None,
                provider="google",
                avatar_url=picture,
                is_verified=True
            )
            is_new_user = True
            logger.info(f"New user created via Google: {email} (ID: {user['id']})")
        else:
            user = update_user_activity(email) or user
            logger.info(f"Existing user signed in via Google: {email} (ID: {user['id']})")

        # Step 3: Automatically dispatch Gmail welcome email notification
        email_sent = True
        try:
            email_res = await email_service.send_welcome_email(
                recipient_email=email,
                user_name=name,
                user_id=user["id"]
            )
            email_sent = email_res.get("status") in ("success", "logged_mock")
        except Exception as mail_err:
            logger.warning(f"Welcome email error (non-fatal): {mail_err}")
            email_sent = False

        # Step 4: Generate JWT token
        access_token_expires = timedelta(days=7)
        access_token = jwt_service.create_access_token(
            data={
                "sub": str(user["id"]),
                "user_id": user["id"],
                "email": user["email"],
                "name": user["name"]
            },
            expires_delta=access_token_expires
        )
        try:
            log_user_activity(
                user_email=user["email"],
                user_name=user["name"],
                action_type="LOGIN",
                action_details="Signed in via Google Authentication"
            )
        except Exception:
            pass

        return GoogleLoginResponse(
            status="success",
            access_token=access_token,
            user={
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "picture": user.get("avatar_url", picture),
                "avatar_url": user.get("avatar_url", picture),
                "provider": "google",
                "is_new": is_new_user,
                "contribution_score": user.get("contribution_score", 0),
                "streak": user.get("streak", 1)
            },
            email_sent=email_sent,
            message="Welcome to BU Prepz AI! Email notification dispatched." if email_sent else "Welcome to BU Prepz AI!"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(jwt_service.verify_token)):
    """Logout current user."""
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me")
async def get_current_user(current_user: dict = Depends(jwt_service.verify_token)):
    """Get authenticated user profile."""
    email = current_user.get("email")
    user = get_user_by_email(email) if email else None
    if not user:
        return {
            "id": current_user.get("user_id", 1),
            "email": email or "student@college.edu",
            "name": current_user.get("name") or (email.split("@")[0].title() if email else "Student"),
            "picture": f"https://api.dicebear.com/7.x/bottts/svg?seed={email or 'Student'}",
            "contribution_score": 0,
            "streak": 1
        }
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("avatar_url"),
        "created_at": user.get("created_at"),
        "contribution_score": user.get("contribution_score", 0),
        "streak": user.get("streak", 1)
    }

@router.get("/email-logs")
async def get_user_email_logs(current_user: dict = Depends(jwt_service.verify_token)):
    """Retrieve audit history of notification emails."""
    logs = get_email_logs(current_user.get("email"))
    return {"logs": logs}
