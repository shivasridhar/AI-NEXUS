from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.dependencies import get_db, get_current_active_user, get_current_workspace
from app.models.tenant import User, Workspace
from app.models.ai_conversation import AIConversation
from app.schemas.ai_conversation import AIConversationCreate, AIConversationUpdate, AIConversationResponse

router = APIRouter()

@router.get("/", response_model=List[AIConversationResponse])
def get_conversations(
    identity_id: str = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all AI conversations for the current workspace.
    Optionally filter by identity_id.
    """
    query = db.query(AIConversation).filter(AIConversation.workspace_id == workspace.id)
    if identity_id:
        query = query.filter(AIConversation.identity_id == identity_id)
    
    return query.order_by(AIConversation.created_at.desc()).all()

@router.get("/{conversation_id}", response_model=AIConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific AI conversation.
    """
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.workspace_id == workspace.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return conversation

@router.post("/", response_model=AIConversationResponse)
def create_conversation(
    conv_in: AIConversationCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new AI conversation.
    """
    messages = []
    if conv_in.message:
        messages.append(conv_in.message.dict())
        
    conversation = AIConversation(
        workspace_id=workspace.id,
        title=conv_in.title,
        identity_id=conv_in.identity_id,
        messages=messages
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.put("/{conversation_id}", response_model=AIConversationResponse)
def update_conversation(
    conversation_id: str,
    conv_in: AIConversationUpdate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a conversation (e.g., append a message).
    """
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.workspace_id == workspace.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if conv_in.title is not None:
        conversation.title = conv_in.title
        
    if conv_in.message:
        # Append to the JSON list
        # We need to create a new list reference for SQLAlchemy to detect the change
        new_messages = list(conversation.messages)
        new_messages.append(conv_in.message.dict())
        conversation.messages = new_messages
        
    db.commit()
    db.refresh(conversation)
    return conversation
