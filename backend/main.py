
import time
from backend.models import Conversation
from backend.models import UserMemory
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.services.memory_search import search_memory
from backend.services.long_term_memory import build_memory_context
from backend.services.memory_extractor import extract_memories
from backend.services.long_term_memory import save_extracted_memories
from backend.database import SessionLocal
from backend.services.rag import answer_question
from backend.services.agent import select_agent_action,execute_agent_action
from backend.services.memory import (
    create_conversation,
    save_message,
    get_conversation_messages,
    get_user_conversation,
    generate_conversation_title,
    delete_conversation
)

from fastapi import FastAPI, Depends, HTTPException
from backend.routers import documents

from backend.routers.auth import (
    router as auth_router,
    get_current_user
)

class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    
    
class MemoryUpdateRequest(BaseModel):
    memory: str
    
        
app = FastAPI(
    title="NexusAI",
    description="Enterprise Agentic Knowledge & Intelligence Platform",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(auth_router)


@app.post("/ask")
def ask_question(
    request: AskRequest,
    current_user = Depends(get_current_user)
):
    db = SessionLocal()
    request_start_time = time.perf_counter()

    try:
        conversation_start_time = time.perf_counter()
        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation = create_conversation(
                db=db,
                user_id=current_user.id,
                title=generate_conversation_title(request.question)
            )

            conversation_id = conversation.id
            
        else:
            get_user_conversation(
                db=db,
                conversation_id=conversation_id,
                user_id=current_user.id
            )    
            
        messages = get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        conversation_history = "\n".join(
            f"{message.role}: {message.content}"
            for message in messages
        )
        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=request.question
        )
        
        memories = search_memory(
            db=db,
            user_id=current_user.id,
            query=request.question,
            top_k=5,
            min_similarity=0.40
        )
        conversation_ms = round(
            (time.perf_counter() - conversation_start_time) * 1000, 2
        )
        memory_start_time = time.perf_counter()

        memory_context = build_memory_context(memories)
        
        memory_retrieval_ms = round(
            (time.perf_counter() - memory_start_time) * 1000, 2
        )
        routing_start_time = time.perf_counter()
        agent_action = select_agent_action(request.question)

        routing_ms = round(
            (time.perf_counter() - routing_start_time) * 1000, 2
        )

        agent_start_time = time.perf_counter()
        agent_status = "running"

        try:
            action_start = time.perf_counter()
            result = execute_agent_action(
                question=request.question,
                db=db,
                user_id=current_user.id,
                action=agent_action,
                is_admin=(current_user.role == "ADMIN"),
                conversation_history=conversation_history,
                memory_context=memory_context
            )
            action_ms = round((time.perf_counter() - action_start) * 1000, 2)
            print(f"DEBUG action execution: {action_ms} ms")
            agent_status = "completed"

        except Exception as e:
            agent_status = "failed"
            raise HTTPException(
                status_code=500,
                detail="Agent execution failed."
            ) from e
        
        save_start = time.perf_counter()
        save_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=result["answer"]
            )
        save_ms = round((time.perf_counter() - save_start) * 1000, 2)
        print(f"DEBUG assistant message save: {save_ms} ms")
        
        agent_execution_ms = round(
                    (time.perf_counter() - agent_start_time) * 1000, 2
                )
        
        total_request_ms = round(
            (time.perf_counter() - request_start_time) * 1000, 2
        )
        
        conversation_text = "\n".join(
            f"{message.role}: {message.content}"
            for message in get_conversation_messages(
                db=db,
                conversation_id=conversation_id,
                user_id=current_user.id
            )
        )
        memory_extraction_start_time = time.perf_counter()

        extracted_memories = extract_memories(conversation_text)

        if extracted_memories:
            save_extracted_memories(
                db=db,
                user_id=current_user.id,
                memories=extracted_memories
            )
            
        memory_extraction_ms = round(
            (time.perf_counter() - memory_extraction_start_time) * 1000, 2
        )    

        return {
            "question": request.question,
            "conversation_id": conversation_id,
            "answer": result["answer"],
            "sources": result["sources"],
            "agent_action": agent_action,
            "agent_status": agent_status,
            "agent_execution_ms": agent_execution_ms,
            "conversation_ms": conversation_ms,
            "memory_retrieval_ms": memory_retrieval_ms,
            "routing_ms": routing_ms,
            "memory_extraction_ms": memory_extraction_ms,
            "total_request_ms": total_request_ms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request."
        ) from e    

    finally:
        db.close()
        
@app.get("/conversations")
def get_my_conversations(
    current_user = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        conversations = (
            db.query(Conversation)
            .filter(
                Conversation.user_id == current_user.id
            )
            .order_by(
                Conversation.created_at.desc()
            )
            .all()
        )

        return [
            {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at
            }
            for conversation in conversations
        ]

    finally:
        db.close()      
        
@app.delete("/conversations/{conversation_id}")
def delete_my_conversation(
    conversation_id: int,
    current_user = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        delete_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        return {
            "message": "Conversation deleted successfully",
            "conversation_id": conversation_id
        }

    finally:
        db.close()          
        
@app.get("/conversations/{conversation_id}")
def get_my_conversation(
    conversation_id: int,
    current_user = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        conversation = get_user_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        messages = get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            user_id=current_user.id
        )

        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at
                }
                for message in messages
            ]
        }

    finally:
        db.close()        
        

@app.get("/memories")
def get_my_memories(current_user=Depends(get_current_user)):
    db = SessionLocal()

    try:
        memories = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == current_user.id)
            .order_by(UserMemory.created_at.desc())
            .all()
        )

        return [
            {
                "id": memory.id,
                "memory": memory.memory,
                "created_at": memory.created_at
            }
            for memory in memories
        ]

    finally:
        db.close()        
        

@app.delete("/memories/{memory_id}")
def delete_my_memory(
    memory_id: int,
    current_user=Depends(get_current_user)
):
    db = SessionLocal()

    try:
        memory = (
            db.query(UserMemory)
            .filter(
                UserMemory.id == memory_id,
                UserMemory.user_id == current_user.id
            )
            .first()
        )

        if not memory:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )

        db.delete(memory)
        db.commit()

        return {
            "message": "Memory deleted successfully",
            "memory_id": memory_id
        }

    finally:
        db.close()        
        

@app.put("/memories/{memory_id}")
def update_my_memory(
    memory_id: int,
    request: MemoryUpdateRequest,
    current_user=Depends(get_current_user)
):
    new_memory_text = request.memory.strip()

    if not new_memory_text:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Memory cannot be empty"
        )

    db = SessionLocal()

    try:
        memory = (
            db.query(UserMemory)
            .filter(
                UserMemory.id == memory_id,
                UserMemory.user_id == current_user.id
            )
            .first()
        )

        if not memory:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )

        from backend.services.embedding import generate_embedding

        memory.memory = new_memory_text
        memory.embedding = generate_embedding(new_memory_text)

        db.commit()
        db.refresh(memory)

        return {
            "message": "Memory updated successfully",
            "memory_id": memory.id,
            "memory": memory.memory
        }

    finally:
        db.close()        
