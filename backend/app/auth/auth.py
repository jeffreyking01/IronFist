"""
IronFist Authentication Module
--------------------------------
Supports two auth modes controlled by the AUTH_MODE environment variable:

  AUTH_MODE=local   — username/password (dev only)
  AUTH_MODE=entra   — Microsoft Entra ID SSO (production)
  AUTH_MODE=both    — both options available (transition/testing)

Local credentials are set via environment variables:
  LOCAL_AUTH_USERNAME  (default: admin)
  LOCAL_AUTH_PASSWORD  (must be set — no default for safety)

Never run AUTH_MODE=local or AUTH_MODE=both in production.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Config from environment ────────────────────────────────────────────────────
AUTH_MODE         = os.getenv("AUTH_MODE", "local").lower()   # local | entra | both
JWT_SECRET        = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM     = "HS256"
JWT_EXPIRE_HOURS  = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Local auth credentials — set these in Secrets Manager / env, never hardcode
LOCAL_USERNAME    = os.getenv("LOCAL_AUTH_USERNAME", "admin")
LOCAL_PASSWORD    = os.getenv("LOCAL_AUTH_PASSWORD", "")      # must be set explicitly

# Entra ID config — only needed when AUTH_MODE=entra or both
ENTRA_TENANT_ID   = os.getenv("ENTRA_TENANT_ID", "")
ENTRA_CLIENT_ID   = os.getenv("ENTRA_CLIENT_ID", "")
ENTRA_CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET", "")

# ── Internals ──────────────────────────────────────────────────────────────────
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
router        = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Models ─────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type:   str
    auth_mode:    str
    username:     str
    role:         str

class TokenData(BaseModel):
    username: Optional[str] = None
    role:     Optional[str] = "analyst"

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthConfig(BaseModel):
    """Returned to frontend so it knows which login options to show."""
    mode:        str
    local_enabled: bool
    entra_enabled: bool


# ── Helpers ────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_local_password(plain: str, stored: str) -> bool:
    """
    In dev, compare plaintext (LOCAL_AUTH_PASSWORD env var).
    In a real deployment, store a bcrypt hash and use pwd_context.verify().
    """
    if not stored:
        logger.warning("LOCAL_AUTH_PASSWORD is not set — local login disabled")
        return False
    return plain == stored


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload  = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role     = payload.get("role", "analyst")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.get("/config", response_model=AuthConfig)
async def auth_config():
    """
    Frontend calls this first to know which login options to render.
    No auth required.
    """
    return AuthConfig(
        mode          = AUTH_MODE,
        local_enabled = AUTH_MODE in ("local", "both"),
        entra_enabled = AUTH_MODE in ("entra", "both"),
    )


@router.post("/local", response_model=Token)
async def local_login(req: LoginRequest):
    """
    Local username/password login.
    Only active when AUTH_MODE=local or AUTH_MODE=both.
    """
    if AUTH_MODE not in ("local", "both"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local authentication is not enabled in this environment",
        )

    if not verify_local_password(req.password, LOCAL_PASSWORD):
        logger.warning("Failed local login attempt for user: %s", req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if req.username != LOCAL_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token({
        "sub":       req.username,
        "role":      "admin",      # local dev account gets full access
        "auth_mode": "local",
    })

    logger.info("Local login successful for user: %s", req.username)
    return Token(
        access_token = token,
        token_type   = "bearer",
        auth_mode    = "local",
        username     = req.username,
        role         = "admin",
    )


@router.post("/token", response_model=Token)
async def token_login(form: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 password flow — used by FastAPI's built-in /docs UI.
    Delegates to local_login internally.
    """
    return await local_login(LoginRequest(
        username=form.username,
        password=form.password,
    ))


@router.get("/entra/login")
async def entra_login_redirect():
    """
    Returns the Entra ID authorization URL.
    Frontend redirects the user here to start the OAuth flow.
    Only active when AUTH_MODE=entra or AUTH_MODE=both.
    """
    if AUTH_MODE not in ("entra", "both"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Entra authentication is not enabled in this environment",
        )
    if not ENTRA_TENANT_ID or not ENTRA_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entra ID is not configured — set ENTRA_TENANT_ID and ENTRA_CLIENT_ID",
        )
    auth_url = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2.0/authorize"
        f"?client_id={ENTRA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri=/api/auth/entra/callback"
        f"&scope=openid+profile+email"
    )
    return {"auth_url": auth_url}


@router.get("/entra/callback")
async def entra_callback(code: str):
    """
    Handles the Entra ID OAuth callback.
    Exchanges the auth code for tokens, validates, issues a local JWT.
    Stub — wire in msal library when Entra config is available.
    """
    if AUTH_MODE not in ("entra", "both"):
        raise HTTPException(status_code=403, detail="Entra auth not enabled")

    # TODO: exchange code for token using msal
    # import msal
    # app = msal.ConfidentialClientApplication(
    #     ENTRA_CLIENT_ID,
    #     authority=f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}",
    #     client_credential=ENTRA_CLIENT_SECRET,
    # )
    # result = app.acquire_token_by_authorization_code(
    #     code, scopes=["User.Read"], redirect_uri="/api/auth/entra/callback"
    # )
    # username = result["id_token_claims"]["preferred_username"]
    # role = map_entra_groups_to_role(result["id_token_claims"].get("groups", []))

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Entra callback not yet wired — set AUTH_MODE=local for dev",
    )


@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Returns current authenticated user info."""
    return {"username": current_user.username, "role": current_user.role}


@router.post("/logout")
async def logout():
    """
    JWT is stateless — logout is handled client-side by deleting the token.
    This endpoint exists for API completeness and future token blocklist support.
    """
    return {"message": "Logged out — delete your local token"}
