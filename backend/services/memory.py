from sqlalchemy.orm import Session

from backend.models import Conversation, Message


def create_conversation(
    db: Session,
    user_id: int,
    title: str | None = None
) -> Conversation:

    conversation = Conversation(
        user_id=user_id,
        title=title
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def save_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str
) -> Message:

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message



def get_conversation_messages(
    db: Session,
    conversation_id: int,
    user_id: int
) -> list[Message]:

    return (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Message.conversation_id == conversation_id,
            Conversation.user_id == user_id
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    
    
from fastapi import HTTPException


def get_user_conversation(
    db: Session,
    conversation_id: int,
    user_id: int
) -> Conversation:

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return conversation    

def generate_conversation_title(question: str) -> str:
    title = question.strip()

    if len(title) > 60:
        title = title[:57] + "..."

    return title

def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: int
) -> None:

    conversation = get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )

    db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).delete()

    db.delete(conversation)
    db.commit()