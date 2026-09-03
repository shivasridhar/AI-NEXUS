import logging
import traceback
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_db, get_current_active_user
from app.core.limiter import limiter
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.redis_client import get_redis_client
from app.models.tenant import Organization, User, Workspace
from app.schemas.auth import UserRegister, UserLogin, Token, AuthMeResponse, GoogleLoginRequest
import secrets
import asyncio

# Google token verification
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError

from app.core.events.bus import event_bus
from app.core.events.contracts import AuditEvent
from app.core.events.event_types import (
    ActorClassification, EventCategory, EventSeverity, EventStatus, ResourceClassification
)
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: provision a completely new tenant account
# ─────────────────────────────────────────────────────────────────────────────
def provision_new_account(
    db: Session,
    email: str,
    full_name: str,
    password_hash: str,
    organization_name: str,
    workspace_name: str,
    provider: str = "LOCAL",
    google_id: str = None,
    profile_picture: str = None,
) -> User:
    # Generate a unique slug
    base_slug = organization_name.lower().replace(" ", "-")
    slug = base_slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=organization_name, slug=slug)
    db.add(org)

    try:
        db.flush()  # Catch unique constraint violations early

        workspace = Workspace(
            name=workspace_name,
            environment="Production",
            organization_id=org.id,
        )
        db.add(workspace)

        user = User(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            google_id=google_id,
            provider=provider,
            profile_picture=profile_picture,
            organization_id=org.id,
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error during account creation for %s: %s", email, traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account creation failed due to a database error. Please try again.",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.error("Unexpected error during account creation: %s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during account creation.",
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# POST /register
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, user_in: UserRegister, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )

    slug = user_in.organization_name.lower().replace(" ", "-")
    org = db.query(Organization).filter(Organization.slug == slug).first()
    if org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists.",
        )

    user = provision_new_account(
        db=db,
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password),
        organization_name=user_in.organization_name,
        workspace_name=user_in.workspace_name,
        provider="LOCAL",
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=refresh_token_expires,
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /login
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()

    if user and user.provider == "GOOGLE" and not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google Sign-In. Please continue with Google or set a password first.",
        )

    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=refresh_token_expires,
    )

    workspace = db.query(Workspace).filter(Workspace.organization_id == user.organization_id).first()
    if workspace:
        try:
            event_bus.publish(
                AuditEvent(
                    workspace_id=str(workspace.id),
                    organization_id=str(user.organization_id),
                    actor=user.email,
                    actor_type=ActorClassification.HUMAN_USER,
                    module="Authentication",
                    action="LOGIN_SUCCESS",
                    category=EventCategory.AUTHENTICATION,
                    severity=EventSeverity.INFO,
                    status=EventStatus.SUCCESS,
                    resource_type=ResourceClassification.SYSTEM,
                )
            )
        except Exception:
            logger.warning("Audit event failed for LOGIN_SUCCESS (non-fatal): %s", traceback.format_exc())

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /google   — full production-hardened Google OAuth flow
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
def google_auth(request: Request, body: GoogleLoginRequest, db: Session = Depends(get_db)):
    # ── 0. Guard: GOOGLE_CLIENT_ID must be configured ────────────────────────
    if not settings.GOOGLE_CLIENT_ID:
        logger.error("Google Sign-In attempted but GOOGLE_CLIENT_ID is not set on the server.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured on this server. Contact the administrator.",
        )

    # ── 1. Verify the Google ID Token ────────────────────────────────────────
    try:
        idinfo = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,  # Tolerate minor clock drift
        )
    except GoogleAuthError as exc:
        logger.warning("Google token verification failed (GoogleAuthError): %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google token. Please sign in again.",
        ) from exc
    except ValueError as exc:
        logger.warning("Google token verification failed (ValueError): %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token. Please sign in again.",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during Google token verification: %s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed due to a server error.",
        ) from exc

    # ── 2. Validate issuer ───────────────────────────────────────────────────
    valid_issuers = {"accounts.google.com", "https://accounts.google.com"}
    if idinfo.get("iss") not in valid_issuers:
        logger.warning("Google token has invalid issuer: %s", idinfo.get("iss"))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token issuer is invalid.",
        )

    # ── 3. Validate email_verified ───────────────────────────────────────────
    if not idinfo.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your Google account email is not verified. Please verify your email with Google first.",
        )

    # ── 4. Extract claims ────────────────────────────────────────────────────
    email: str = idinfo.get("email", "").lower().strip()
    google_id: str = idinfo.get("sub", "")
    name: str = idinfo.get("name", "Google User")
    picture: str = idinfo.get("picture", "")

    if not email or not google_id:
        logger.error("Google token missing required claims. idinfo keys: %s", list(idinfo.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token is missing required user information.",
        )

    # ── 5. Resolve user (lookup → link → create) ─────────────────────────────
    try:
        user: User = db.query(User).filter(User.google_id == google_id).first()

        if not user:
            # No user with this google_id — check by email
            user = db.query(User).filter(User.email == email).first()

            if user:
                # Email match found
                if user.google_id and user.google_id != google_id:
                    # This email is already linked to a DIFFERENT Google account
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This email is already linked to a different Google account.",
                    )

                # Safe to link: either LOCAL account or same google_id (idempotent)
                user.google_id = google_id
                user.provider = "GOOGLE"
                if picture:
                    user.profile_picture = picture
                db.commit()
                db.refresh(user)
                logger.info("Google account linked to existing user: %s", email)

                try:
                    event_bus.publish(
                        AuditEvent(
                            workspace_id="SYSTEM",
                            organization_id=str(user.organization_id),
                            actor=user.email,
                            actor_type=ActorClassification.HUMAN_USER,
                            module="Authentication",
                            action="ACCOUNT_LINKED",
                            category=EventCategory.AUTHENTICATION,
                            severity=EventSeverity.INFO,
                            status=EventStatus.SUCCESS,
                            resource_type=ResourceClassification.SYSTEM,
                        )
                    )
                except Exception:
                    logger.warning("Audit event ACCOUNT_LINKED failed (non-fatal): %s", traceback.format_exc())

            else:
                # Brand-new user — provision full account
                logger.info("Provisioning new Google account for: %s", email)
                random_pw = secrets.token_urlsafe(32)
                hashed_pw = hash_password(random_pw)

                user = provision_new_account(
                    db=db,
                    email=email,
                    full_name=name,
                    password_hash=hashed_pw,
                    organization_name=f"{name}'s Organization",
                    workspace_name="Default Workspace",
                    provider="GOOGLE",
                    google_id=google_id,
                    profile_picture=picture,
                )

                try:
                    event_bus.publish(
                        AuditEvent(
                            workspace_id="SYSTEM",
                            organization_id=str(user.organization_id),
                            actor=user.email,
                            actor_type=ActorClassification.HUMAN_USER,
                            module="Authentication",
                            action="ACCOUNT_CREATED",
                            category=EventCategory.AUTHENTICATION,
                            severity=EventSeverity.INFO,
                            status=EventStatus.SUCCESS,
                            resource_type=ResourceClassification.SYSTEM,
                        )
                    )
                except Exception:
                    logger.warning("Audit event ACCOUNT_CREATED failed (non-fatal): %s", traceback.format_exc())

    except HTTPException:
        raise  # Re-raise our own controlled HTTP exceptions untouched
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error during Google auth for %s: %s", email, traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during sign-in. Please try again.",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.error("Unexpected error during Google auth for %s: %s", email, traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred during Google Sign-In.",
        ) from exc

    # ── 6. Active check ───────────────────────────────────────────────────────
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator.",
        )

    # ── 7. Issue JWT ─────────────────────────────────────────────────────────
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=refresh_token_expires,
    )

    # ── 8. Audit: login success ───────────────────────────────────────────────
    workspace = db.query(Workspace).filter(Workspace.organization_id == user.organization_id).first()
    if workspace:
        try:
            event_bus.publish(
                AuditEvent(
                    workspace_id=str(workspace.id),
                    organization_id=str(user.organization_id),
                    actor=user.email,
                    actor_type=ActorClassification.HUMAN_USER,
                    module="Authentication",
                    action="LOGIN_SUCCESS",
                    category=EventCategory.AUTHENTICATION,
                    severity=EventSeverity.INFO,
                    status=EventStatus.SUCCESS,
                    resource_type=ResourceClassification.SYSTEM,
                )
            )
        except Exception:
            logger.warning("Audit event LOGIN_SUCCESS failed (non-fatal): %s", traceback.format_exc())

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# ─────────────────────────────────────────────────────────────────────────────
# GET /me
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=AuthMeResponse)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    workspace = db.query(Workspace).filter(Workspace.organization_id == current_user.organization_id).first()

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "organization_id": str(current_user.organization_id),
        },
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
        }
        if org
        else {},
        "workspace": {
            "id": str(workspace.id),
            "name": workspace.name,
            "environment": workspace.environment,
        }
        if workspace
        else {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /logout — blacklists the current token via Redis
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel as _BM

class _LogoutRequest(_BM):
    refresh_token: str = ""

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: _LogoutRequest = _LogoutRequest(),
    current_user: User = Depends(get_current_active_user),
):
    try:
        redis = await get_redis_client()
        # Blacklist the refresh token if provided
        if body.refresh_token:
            try:
                payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
                jti = payload.get("jti", "")
                ttl = max(int(payload.get("exp", 0) - datetime.now(timezone.utc).timestamp()), 0)
                if jti and ttl > 0:
                    await redis.setex(f"blacklist:{jti}", ttl, "1")
            except Exception:
                pass  # Invalid refresh token — still proceed with logout
    except Exception:
        logger.warning("Redis unavailable during logout (non-fatal)")

    return {"message": "Successfully logged out"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /refresh — issues new access token from valid refresh token
# ─────────────────────────────────────────────────────────────────────────────
class _RefreshRequest(_BM):
    refresh_token: str

@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(body: _RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
        jti = payload.get("jti", "")
        if not user_id:
            raise credentials_exception

        # Check if token is blacklisted
        try:
            redis = await get_redis_client()
            if jti and await redis.get(f"blacklist:{jti}"):
                raise credentials_exception
        except credentials_exception.__class__:
            raise
        except Exception:
            pass  # Redis down — allow refresh (fail open for availability)

    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        expires_delta=access_token_expires,
    )
    return {"access_token": new_access_token, "token_type": "bearer"}
