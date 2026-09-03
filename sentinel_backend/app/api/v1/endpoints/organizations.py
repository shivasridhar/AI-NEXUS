from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.api.dependencies import get_db, get_current_active_user, get_current_workspace, require_admin
from app.models.tenant import Organization, Workspace, User
from pydantic import BaseModel

router = APIRouter()

@router.get("/me")
def get_my_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    workspaces = db.query(Workspace).filter(Workspace.organization_id == org.id).all()
    
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "workspaces": [{"id": str(w.id), "name": w.name, "environment": w.environment} for w in workspaces]
    }

class UpdateOrgRequest(BaseModel):
    name: str

@router.put("/me")
def update_my_organization(
    request: UpdateOrgRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    org.name = request.name
    db.commit()
    return {"message": "Organization updated successfully"}
