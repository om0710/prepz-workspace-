import os
import logging
import httpx
from fastapi import HTTPException

logger = logging.getLogger("google_auth_service")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or "585299422541-edqtcaaoljev3op2cffl98jfvr8asn56.apps.googleusercontent.com"

class GoogleAuthService:
    """Handle Google OAuth verification and token parsing."""

    @staticmethod
    async def verify_google_token_async(token_str: str) -> dict:
        """
        Verify Google ID token or Access Token and extract user profile info.
        """
        if not token_str or not token_str.strip():
            raise HTTPException(status_code=400, detail="Google token is required")

        token = token_str.strip()

        # 1. Try google.oauth2 id_token library
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            email = idinfo.get("email", "").strip().lower()
            if not email:
                raise ValueError("Email missing from token payload")
            return {
                "google_id": idinfo.get("sub"),
                "email": email,
                "name": idinfo.get("name") or email.split("@")[0].title(),
                "picture": idinfo.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                "email_verified": idinfo.get("email_verified", True)
            }
        except Exception as id_err:
            logger.debug(f"google.oauth2 token verification fallback to HTTP: {id_err}")

        # 2. Fallback to Google tokeninfo and userinfo endpoints via HTTPX
        async with httpx.AsyncClient(timeout=8) as client:
            # Check as ID token
            try:
                resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email", "").strip().lower()
                    if email:
                        return {
                            "google_id": data.get("sub"),
                            "email": email,
                            "name": data.get("name") or email.split("@")[0].title(),
                            "picture": data.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                            "email_verified": data.get("email_verified", True)
                        }
            except Exception:
                pass

            # Check as Access token
            try:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email", "").strip().lower()
                    if email:
                        return {
                            "google_id": data.get("id"),
                            "email": email,
                            "name": data.get("name") or email.split("@")[0].title(),
                            "picture": data.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                            "email_verified": data.get("verified_email", True)
                        }
            except Exception:
                pass

        raise HTTPException(status_code=401, detail="Invalid Google authentication token")

    @classmethod
    def verify_google_token(cls, id_token_str: str) -> dict:
        """Synchronous wrapper for token verification."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running loop, use google-auth standard library
                from google.oauth2 import id_token
                from google.auth.transport import requests
                idinfo = id_token.verify_oauth2_token(id_token_str, requests.Request(), GOOGLE_CLIENT_ID)
                email = idinfo.get("email", "").strip().lower()
                return {
                    "google_id": idinfo.get("sub"),
                    "email": email,
                    "name": idinfo.get("name") or email.split("@")[0].title(),
                    "picture": idinfo.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                    "email_verified": idinfo.get("email_verified", True)
                }
            else:
                return loop.run_until_complete(cls.verify_google_token_async(id_token_str))
        except Exception:
            # Direct HTTPX synchronous check
            with httpx.Client(timeout=8) as client:
                resp = client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}")
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email", "").strip().lower()
                    if email:
                        return {
                            "google_id": data.get("sub"),
                            "email": email,
                            "name": data.get("name") or email.split("@")[0].title(),
                            "picture": data.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                            "email_verified": data.get("email_verified", True)
                        }
            raise HTTPException(status_code=401, detail="Invalid Google authentication token")

google_auth_service = GoogleAuthService()
