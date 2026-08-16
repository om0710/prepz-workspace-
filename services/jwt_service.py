import os
import json
import base64
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "prepz_super_secret_cryptographic_key_2026_x89q"
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

security_bearer = HTTPBearer(auto_error=False)

class JWTService:
    """Handle cryptographic JWT token generation and verification."""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create secure signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": int(expire.timestamp())})

        # Try python-jose
        try:
            from jose import jwt
            return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception:
            # Cryptographically secure fallback
            payload_bytes = json.dumps(to_encode, sort_keys=True).encode("utf-8")
            b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
            sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            return f"{b64_payload}.{sig}"

    @staticmethod
    def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
        """Verify JWT token and extract user claims."""
        credential_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not credentials or not credentials.credentials:
            raise credential_exception

        token = credentials.credentials.strip()

        # Try python-jose
        try:
            from jose import jwt, JWTError
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if user_id is None and not payload.get("email"):
                raise credential_exception
            return {
                "user_id": int(user_id) if user_id and str(user_id).isdigit() else 1,
                "email": payload.get("email", ""),
                "name": payload.get("name", "")
            }
        except Exception:
            pass

        # Verify custom signed token fallback
        try:
            if "." in token:
                parts = token.split(".")
                if len(parts) == 2:
                    b64_p, signature = parts
                    expected = hmac.new(SECRET_KEY.encode("utf-8"), b64_p.encode("utf-8"), hashlib.sha256).hexdigest()
                    if hmac.compare_digest(expected, signature):
                        padding = "=" * (-len(b64_p) % 4)
                        p_data = json.loads(base64.urlsafe_b64decode(b64_p + padding).decode("utf-8"))
                        if p_data.get("exp") and p_data["exp"] < time.time():
                            raise credential_exception
                        return {
                            "user_id": int(p_data.get("sub", 1)) if str(p_data.get("sub", "")).isdigit() else 1,
                            "email": p_data.get("email", ""),
                            "name": p_data.get("name", "")
                        }
        except Exception:
            pass

        raise credential_exception

jwt_service = JWTService()
