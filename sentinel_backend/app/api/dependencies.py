from typing import Generator
from app.db.session import SessionLocal
from app.graph.session import neo4j_manager

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_neo4j_session() -> Generator:
    try:
        session = neo4j_manager.get_session()
        yield session
    finally:
        session.close()

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.tenant import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def decode_and_verify_token(token: str) -> str:
    """
    Decodes a JWT token and returns the subject (user_id).
    Raises jwt.exceptions.InvalidTokenError (or subclass) if invalid.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    user_id: str = payload.get("sub")
    if user_id is None:
        raise JWTError("Token subject is missing")
    return user_id

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_and_verify_token(token)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ── RBAC: Role-Based Access Control ─────────────────────────────────────────
from typing import List

class RoleChecker:
    """
    Dependency that enforces role-based access control.
    Usage: Depends(RoleChecker(["admin"])) or Depends(RoleChecker(["admin", "analyst"]))
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(self.allowed_roles)}",
            )
        return current_user

# Pre-built role dependencies for convenience
require_admin = RoleChecker(["admin"])
require_analyst = RoleChecker(["admin", "analyst"])
require_viewer = RoleChecker(["admin", "analyst", "viewer"])


from fastapi import Header
from app.models.tenant import Workspace

def get_current_workspace(
    x_workspace_id: str = Header(..., description="The ID of the active workspace"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Workspace:
    try:
        import uuid
        workspace_uuid = uuid.UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")
        
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_uuid,
        Workspace.organization_id == current_user.organization_id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Workspace access denied or not found")
        
    return workspace
